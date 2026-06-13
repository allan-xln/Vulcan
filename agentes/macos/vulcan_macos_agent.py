#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


APP_VERSION = "0.1.0-macos-skeleton"
APP_SUPPORT = Path.home() / "Library" / "Application Support" / "Vulcan" / "Agent"
LOG_DIR = Path.home() / "Library" / "Logs" / "VulcanAgent"
CONFIG_PATH = APP_SUPPORT / "config.json"
QUEUE_PATH = APP_SUPPORT / "queue.jsonl"
LOG_PATH = LOG_DIR / "agent.log"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    APP_SUPPORT.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    ensure_dirs()
    line = f"{now_iso()} {message}\n"
    LOG_PATH.open("a", encoding="utf-8").write(line)
    print(line, end="")


def read_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def write_config(config: dict) -> None:
    ensure_dirs()
    CONFIG_PATH.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    CONFIG_PATH.chmod(0o600)


def request_json(method: str, url: str, payload: dict | None = None, timeout: int = 15) -> dict:
    body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json", "User-Agent": f"VulcanMacAgent/{APP_VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def active_application() -> tuple[str, str]:
    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=4, check=True)
        app = result.stdout.strip() or "macOS"
        return app, "medium"
    except (subprocess.SubprocessError, FileNotFoundError):
        return "macOS - permissao pendente", "blocked_by_os"


def base_payload(config: dict) -> dict:
    device_id = config.get("deviceId") or str(uuid4())
    config["deviceId"] = device_id
    write_config(config)
    return {
        "tenantId": config["tenantId"],
        "enrollmentToken": config["enrollmentToken"],
        "deviceId": device_id,
        "membershipId": config.get("membershipId"),
        "machineFingerprint": config.get("machineFingerprint") or f"macos-{socket.gethostname()}-{os.getuid()}",
        "hostname": socket.gethostname(),
        "os": f"macOS {platform.mac_ver()[0] or platform.release()}",
        "agentVersion": APP_VERSION,
        "localIp": local_ip(),
        "osUser": os.environ.get("USER"),
    }


def local_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def enroll() -> None:
    config = read_config()
    payload = base_payload(config)
    payload["metadata"] = {
        "privacy": "O Vulcan mede fluxo operacional, nao conteudo pessoal.",
        "platform": "macos",
        "adoptionStatus": "pending" if not config.get("membershipId") else "adopted",
    }
    response = request_json("POST", f"{config['backendUrl'].rstrip('/')}/agent/enroll", payload)
    if response.get("deviceId"):
        config["deviceId"] = response["deviceId"]
        write_config(config)
    log(f"enroll ok device={config.get('deviceId')}")


def heartbeat() -> None:
    config = read_config()
    app_name, quality = active_application()
    payload = base_payload(config)
    payload.update(
        {
            "status": "online",
            "queueDepth": queue_depth(),
            "collectionQuality": quality,
            "metadata": {
                "activeApp": app_name,
                "privacy": "sem tecla, senha, audio, webcam, screenshot ou conteudo privado",
            },
        }
    )
    request_json("POST", f"{config['backendUrl'].rstrip('/')}/agent/heartbeat", payload)
    log(f"heartbeat ok app={app_name} quality={quality}")


def queue_depth() -> int:
    if not QUEUE_PATH.exists():
        return 0
    return sum(1 for _ in QUEUE_PATH.open("r", encoding="utf-8"))


def enqueue_event(config: dict) -> None:
    app_name, quality = active_application()
    event = {
        "eventId": str(uuid4()),
        "eventType": "foreground_application_change",
        "appName": app_name,
        "startedAt": now_iso(),
        "endedAt": now_iso(),
        "durationSeconds": 60,
        "metadata": {"quality": quality, "platform": "macos", "privacy": "flow_only"},
    }
    ensure_dirs()
    QUEUE_PATH.open("a", encoding="utf-8").write(json.dumps(event) + "\n")
    log(f"queued event app={app_name} quality={quality}")


def sync() -> None:
    config = read_config()
    if not QUEUE_PATH.exists():
        heartbeat()
        return
    events = [json.loads(line) for line in QUEUE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not events:
        heartbeat()
        return
    payload = base_payload(config)
    payload["events"] = events[: int(config.get("syncBatchSize", 50))]
    request_json("POST", f"{config['backendUrl'].rstrip('/')}/agent/sync", payload)
    remaining = events[len(payload["events"]) :]
    QUEUE_PATH.write_text("\n".join(json.dumps(item) for item in remaining) + ("\n" if remaining else ""), encoding="utf-8")
    log(f"sync ok sent={len(payload['events'])} remaining={len(remaining)}")


def status() -> None:
    config = read_config()
    payload = {
        "configured": bool(config.get("backendUrl") and config.get("tenantId") and config.get("enrollmentToken")),
        "backendUrl": config.get("backendUrl"),
        "tenantId": config.get("tenantId"),
        "deviceId": config.get("deviceId"),
        "membershipId": config.get("membershipId"),
        "queueDepth": queue_depth(),
        "log": str(LOG_PATH),
        "privacy": "O Vulcan mede fluxo operacional, nao conteudo pessoal.",
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def run_loop() -> None:
    config = read_config()
    interval = int(config.get("intervalSeconds", 60))
    while True:
        try:
            enqueue_event(config)
            sync()
        except (urllib.error.URLError, OSError, RuntimeError, KeyError) as exc:
            log(f"sync deferred error={exc}")
        time.sleep(interval)


def configure(args: argparse.Namespace) -> None:
    config = read_config()
    config.update(
        {
            "backendUrl": args.backend_url,
            "tenantId": args.tenant_id,
            "enrollmentToken": args.enrollment_token,
            "membershipId": args.membership_id,
            "syncBatchSize": args.sync_batch_size,
            "intervalSeconds": args.interval_seconds,
        }
    )
    write_config({key: value for key, value in config.items() if value is not None})
    log("config ok")


def main() -> int:
    parser = argparse.ArgumentParser(description="Vulcan macOS Agent skeleton")
    sub = parser.add_subparsers(dest="command", required=True)
    cfg = sub.add_parser("configure")
    cfg.add_argument("--backend-url", required=True)
    cfg.add_argument("--tenant-id", required=True)
    cfg.add_argument("--enrollment-token", required=True)
    cfg.add_argument("--membership-id")
    cfg.add_argument("--sync-batch-size", type=int, default=50)
    cfg.add_argument("--interval-seconds", type=int, default=60)
    sub.add_parser("enroll")
    sub.add_parser("heartbeat")
    sub.add_parser("sync")
    sub.add_parser("status")
    sub.add_parser("run")
    args = parser.parse_args()
    if args.command == "configure":
        configure(args)
    elif args.command == "enroll":
        enroll()
    elif args.command == "heartbeat":
        heartbeat()
    elif args.command == "sync":
        sync()
    elif args.command == "status":
        status()
    elif args.command == "run":
        run_loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
