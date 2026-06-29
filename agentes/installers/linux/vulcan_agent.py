#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import platform
import resource
import re
import shutil
import sqlite3
import socket
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, parse, request


VERSION = "0.2.0"
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000301"
DEFAULT_POLICY = {
    "collectAppName": True,
    "collectWindowTitle": False,
    "collectIdleTime": True,
    "collectSessionEvents": True,
    "collectBrowserDomain": False,
    "collectBrowserUrl": False,
    "collectBrowserHistory": False,
    "collectBrowserPageTitle": False,
    "collectProcessList": False,
    "collectSystemMetrics": True,
    "redactSensitiveTerms": True,
    "browserHistoryIntervalSeconds": 300,
    "browserHistoryLookbackMinutes": 60,
    "browserHistoryMaxEvents": 50,
    "syncIntervalSeconds": 30,
    "heartbeatIntervalSeconds": 60,
    "syncBatchSize": 100,
    "httpTimeoutSeconds": 30,
    "offlineQueueEnabled": True,
    "maxOfflineQueueSize": 10000,
    "allowUserPause": True,
    "showTrayStatus": False,
    "privacyMode": "standard",
    "idleThresholdSeconds": 300,
}
SENSITIVE_PATTERNS = [
    "password",
    "senha",
    "secret",
    "token",
    "cookie",
    "login",
    "whatsapp",
    "telegram",
    "signal",
    "bank",
    "banco",
    "cpf",
    "cnpj",
    "cartao",
    "card",
    "private",
    "privado",
    "confidential",
    "confidencial",
]
ADULT_DOMAIN_PATTERNS = [
    "porn",
    "xvideos",
    "xnxx",
    "xhamster",
    "redtube",
    "youporn",
    "tube8",
    "spankbang",
    "brazzers",
    "sex",
    "adult",
    "onlyfans",
    "privacy.com.br",
]
WINDOWS_EPOCH_OFFSET_SECONDS = 11644473600


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "vulcan" / "agent"


def data_dir() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "vulcan-agent"


def config_path() -> Path:
    return Path(os.environ.get("VULCAN_AGENT_CONFIG", config_dir() / "config.json"))


def policy_path() -> Path:
    return Path(os.environ.get("VULCAN_AGENT_POLICY", config_dir() / "agent-policy.json"))


def queue_path() -> Path:
    return data_dir() / "queue" / "events.jsonl"


def browser_state_path() -> Path:
    return data_dir() / "browser-history-state.json"


def log_path() -> Path:
    return data_dir() / "logs" / "agent.log"


def log(level: str, message: str, **metadata: object) -> None:
    log_path().parent.mkdir(parents=True, exist_ok=True)
    entry = {"level": level, "message": message, "createdAt": iso_now(), "metadata": metadata}
    with log_path().open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def hostname() -> str:
    return socket.gethostname() or "linux-host"


def current_user() -> str:
    return getpass.getuser()


def machine_fingerprint(tenant_id: str, backend_url: str) -> str:
    source = "|".join([tenant_id, backend_url, hostname(), current_user(), platform.platform()])
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def default_config(args: argparse.Namespace) -> dict:
    tenant_id = args.tenant_id or DEFAULT_TENANT_ID
    backend_url = (args.backend_url or "http://localhost:3001").rstrip("/")
    return {
        "backendUrl": backend_url,
        "tenantId": tenant_id,
        "enrollmentToken": args.enrollment_token or "vulcan-local-enrollment-token",
        "deviceId": str(uuid.uuid4()),
        "machineFingerprint": machine_fingerprint(tenant_id, backend_url),
        "hostname": hostname(),
        "osUser": current_user(),
        "osVersion": platform.platform(),
        "linkedUser": args.linked_user or current_user(),
        "membershipId": args.membership_id or "",
        "roleLevel": args.role_level or "Operador",
        "department": args.department or "Operacoes",
        "collectWindowTitle": bool(args.collect_window_title),
        "policyPath": str(policy_path()),
        "heartbeatIntervalSeconds": max(int(args.heartbeat_interval or 60), 15),
        "syncIntervalSeconds": max(int(args.sync_interval or 30), 15),
        "installedAt": iso_now(),
    }


def default_policy(args: argparse.Namespace | None = None) -> dict:
    policy = dict(DEFAULT_POLICY)
    if args and getattr(args, "corporate_monitoring", False):
        policy.update(
            {
                "collectWindowTitle": True,
                "collectBrowserDomain": True,
                "collectBrowserUrl": True,
                "collectBrowserHistory": True,
                "collectBrowserPageTitle": True,
                "collectProcessList": True,
                "privacyMode": "corporate",
                "showTrayStatus": True,
                "allowUserPause": False,
            }
        )
    if args and getattr(args, "collect_window_title", False):
        policy["collectWindowTitle"] = True
    if args and getattr(args, "collect_browser_domain", False):
        policy["collectBrowserDomain"] = True
    if args and getattr(args, "collect_browser_url", False):
        policy["collectBrowserUrl"] = True
    if args and getattr(args, "collect_browser_history", False):
        policy["collectBrowserHistory"] = True
    if args and getattr(args, "collect_process_list", False):
        policy["collectProcessList"] = True
    return policy


def load_config() -> dict:
    with config_path().open("r", encoding="utf-8") as file:
        return json.load(file)


def save_config(config: dict) -> None:
    config_path().parent.mkdir(parents=True, exist_ok=True)
    with config_path().open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2, ensure_ascii=False)


def save_policy(policy: dict, path: Path | None = None) -> None:
    path = path or policy_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(policy, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_policy(config: dict | None = None) -> dict:
    path = Path((config or {}).get("policyPath") or policy_path())
    if not path.exists():
        save_policy(default_policy(), path)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        loaded = {}
    policy = dict(DEFAULT_POLICY)
    policy.update({key: loaded.get(key, value) for key, value in DEFAULT_POLICY.items()})
    policy["syncIntervalSeconds"] = max(int(policy.get("syncIntervalSeconds") or 30), 15)
    policy["heartbeatIntervalSeconds"] = max(int(policy.get("heartbeatIntervalSeconds") or 60), 15)
    policy["syncBatchSize"] = max(min(int(policy.get("syncBatchSize") or 100), 500), 10)
    policy["httpTimeoutSeconds"] = max(min(int(policy.get("httpTimeoutSeconds") or 30), 120), 5)
    policy["maxOfflineQueueSize"] = max(int(policy.get("maxOfflineQueueSize") or 10000), 100)
    policy["idleThresholdSeconds"] = max(int(policy.get("idleThresholdSeconds") or 300), 30)
    policy["browserHistoryIntervalSeconds"] = max(int(policy.get("browserHistoryIntervalSeconds") or 300), 60)
    policy["browserHistoryLookbackMinutes"] = max(min(int(policy.get("browserHistoryLookbackMinutes") or 60), 1440), 5)
    policy["browserHistoryMaxEvents"] = max(min(int(policy.get("browserHistoryMaxEvents") or 50), 250), 1)
    return policy


def sanitize_title(title: str, collect: bool, redact: bool = True) -> str:
    if not collect or not title:
        return ""
    lowered = title.lower()
    if redact:
        for pattern in SENSITIVE_PATTERNS:
            if pattern in lowered:
                log("info", "window title redacted by policy", pattern=pattern)
                return "[redacted]"
    return title[:180]


def normalize_browser_url(value: str, collect_url: bool, collect_domain: bool) -> tuple[str, str, bool]:
    if not value or not (collect_url or collect_domain):
        return "", "", False
    match = re.search(r"https?://[^\s)>\"]+", value)
    raw_url = match.group(0) if match else value
    parsed = parse.urlsplit(raw_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "", "", False
    domain = parsed.netloc.lower()
    if "@" in domain:
        domain = domain.rsplit("@", 1)[-1]
    domain = domain.split(":", 1)[0].strip(".")
    path = parsed.path or ""
    adult_signal = is_adult_domain(domain)
    path_lower = path.lower()
    if any(pattern in path_lower for pattern in SENSITIVE_PATTERNS):
        safe_url = f"{parsed.scheme}://{domain}/" if collect_url else ""
    else:
        safe_url = f"{parsed.scheme}://{domain}{path}" if collect_url else ""
    return domain if collect_domain else "", safe_url[:500], adult_signal


def sanitize_url(value: str, collect_url: bool, collect_domain: bool) -> tuple[str, str]:
    domain, safe_url, _adult_signal = normalize_browser_url(value, collect_url, collect_domain)
    return domain, safe_url


def is_adult_domain(domain: str) -> bool:
    normalized = domain.lower().removeprefix("www.")
    return any(pattern in normalized for pattern in ADULT_DOMAIN_PATTERNS)


def app_category(app: str) -> str:
    lowered = app.lower()
    categories = {
        "navegador": ["chrome", "chromium", "firefox", "brave", "edge", "opera", "vivaldi"],
        "comunicação": ["slack", "teams", "discord", "zoom", "meet", "telegram", "whatsapp"],
        "desenvolvimento": ["code", "vscode", "cursor", "jetbrains", "idea", "pycharm", "terminal", "gnome-terminal", "konsole"],
        "documentos": ["libreoffice", "writer", "calc", "excel", "word", "sheets"],
        "erp/crm": ["erp", "sap", "totvs", "crm", "salesforce"],
        "sistema": ["desktop", "gnome", "kde", "xfce", "shell"],
    }
    for category, terms in categories.items():
        if any(term in lowered for term in terms):
            return category
    return "operacional"


def collection_environment() -> dict:
    return {
        "sessionType": os.environ.get("XDG_SESSION_TYPE") or "desconhecido",
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "desconhecido",
        "waylandDisplay": bool(os.environ.get("WAYLAND_DISPLAY")),
        "display": bool(os.environ.get("DISPLAY")),
    }


def run_text(command: list[str], timeout: int = 3) -> str:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def copy_sqlite_database(source: Path) -> Path | None:
    if not source.exists() or not source.is_file():
        return None
    try:
        temp = tempfile.NamedTemporaryFile(prefix="vulcan-browser-", suffix=".sqlite", delete=False)
        temp_path = Path(temp.name)
        temp.close()
        shutil.copy2(source, temp_path)
        return temp_path
    except OSError as exc:
        log("warning", "failed to copy browser history database", path=str(source), error=str(exc))
        return None


def chrome_time_to_datetime(value: int | float | None) -> datetime | None:
    if not value:
        return None
    try:
        timestamp = (float(value) / 1_000_000) - WINDOWS_EPOCH_OFFSET_SECONDS
        return datetime.fromtimestamp(timestamp, timezone.utc)
    except (OSError, ValueError, OverflowError):
        return None


def firefox_time_to_datetime(value: int | float | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1_000_000, timezone.utc)
    except (OSError, ValueError, OverflowError):
        return None


def browser_profiles() -> list[dict]:
    home = Path.home()
    profiles: list[dict] = []
    chromium_roots = [
        ("Google Chrome", home / ".config" / "google-chrome"),
        ("Chromium", home / ".config" / "chromium"),
        ("Brave", home / ".config" / "BraveSoftware" / "Brave-Browser"),
        ("Microsoft Edge", home / ".config" / "microsoft-edge"),
    ]
    for browser, root in chromium_roots:
        if not root.exists():
            continue
        for history in root.glob("*/History"):
            if history.parent.name in {"Crashpad", "CertificateRevocation", "ShaderCache"}:
                continue
            profiles.append({"browser": browser, "engine": "chromium", "profile": history.parent.name, "path": history})
    firefox_root = home / ".mozilla" / "firefox"
    if firefox_root.exists():
        for places in firefox_root.glob("*/places.sqlite"):
            profiles.append({"browser": "Firefox", "engine": "firefox", "profile": places.parent.name, "path": places})
    return profiles


def read_browser_state() -> dict:
    path = browser_state_path()
    if not path.exists():
        return {"seen": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"seen": []}
    if not isinstance(payload, dict):
        return {"seen": []}
    payload.setdefault("seen", [])
    return payload


def save_browser_state(state: dict) -> None:
    state["seen"] = list(dict.fromkeys(state.get("seen", []) or []))[-10000:]
    browser_state_path().parent.mkdir(parents=True, exist_ok=True)
    browser_state_path().write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def browser_visit_key(browser: str, profile: str, visited_at: datetime, safe_url: str, domain: str) -> str:
    source = "|".join([browser, profile, visited_at.isoformat(), safe_url or domain])
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def fetch_chromium_history(profile: dict, since: datetime, limit: int) -> list[dict]:
    copied = copy_sqlite_database(Path(profile["path"]))
    if not copied:
        return []
    threshold = int((since.timestamp() + WINDOWS_EPOCH_OFFSET_SECONDS) * 1_000_000)
    rows: list[dict] = []
    try:
        conn = sqlite3.connect(f"file:{copied}?mode=ro", uri=True, timeout=2)
        try:
            cursor = conn.execute(
                """
                select urls.url, coalesce(urls.title, ''), visits.visit_time
                from visits
                join urls on urls.id = visits.url
                where visits.visit_time >= ?
                order by visits.visit_time desc
                limit ?
                """,
                (threshold, limit),
            )
            for url, title, visited_raw in cursor.fetchall():
                visited_at = chrome_time_to_datetime(visited_raw)
                if visited_at:
                    rows.append({"url": str(url or ""), "title": str(title or ""), "visitedAt": visited_at})
        finally:
            conn.close()
    except sqlite3.Error as exc:
        log("warning", "failed to read chromium history", browser=profile["browser"], profile=profile["profile"], error=str(exc))
    finally:
        try:
            copied.unlink(missing_ok=True)
        except OSError:
            pass
    return rows


def fetch_firefox_history(profile: dict, since: datetime, limit: int) -> list[dict]:
    copied = copy_sqlite_database(Path(profile["path"]))
    if not copied:
        return []
    threshold = int(since.timestamp() * 1_000_000)
    rows: list[dict] = []
    try:
        conn = sqlite3.connect(f"file:{copied}?mode=ro", uri=True, timeout=2)
        try:
            cursor = conn.execute(
                """
                select moz_places.url, coalesce(moz_places.title, ''), moz_historyvisits.visit_date
                from moz_historyvisits
                join moz_places on moz_places.id = moz_historyvisits.place_id
                where moz_historyvisits.visit_date >= ?
                order by moz_historyvisits.visit_date desc
                limit ?
                """,
                (threshold, limit),
            )
            for url, title, visited_raw in cursor.fetchall():
                visited_at = firefox_time_to_datetime(visited_raw)
                if visited_at:
                    rows.append({"url": str(url or ""), "title": str(title or ""), "visitedAt": visited_at})
        finally:
            conn.close()
    except sqlite3.Error as exc:
        log("warning", "failed to read firefox history", browser=profile["browser"], profile=profile["profile"], error=str(exc))
    finally:
        try:
            copied.unlink(missing_ok=True)
        except OSError:
            pass
    return rows


def collect_browser_history_events(config: dict, policy: dict, now: datetime) -> list[dict]:
    if not policy.get("collectBrowserHistory"):
        return []
    collect_domain = bool(policy.get("collectBrowserDomain"))
    collect_url = bool(policy.get("collectBrowserUrl"))
    if not (collect_domain or collect_url):
        return []
    max_events = int(policy.get("browserHistoryMaxEvents") or 50)
    lookback = int(policy.get("browserHistoryLookbackMinutes") or 60)
    since = now.timestamp() - (lookback * 60)
    since_dt = datetime.fromtimestamp(since, timezone.utc)
    state = read_browser_state()
    seen = set(state.get("seen", []) or [])
    collected: list[dict] = []
    for profile in browser_profiles():
        remaining = max_events - len(collected)
        if remaining <= 0:
            break
        if profile["engine"] == "chromium":
            visits = fetch_chromium_history(profile, since_dt, remaining * 3)
        else:
            visits = fetch_firefox_history(profile, since_dt, remaining * 3)
        for visit in visits:
            domain, safe_url, adult_signal = normalize_browser_url(str(visit["url"]), collect_url, collect_domain)
            if not domain and not safe_url:
                continue
            visited_at = visit["visitedAt"]
            key = browser_visit_key(str(profile["browser"]), str(profile["profile"]), visited_at, safe_url, domain)
            if key in seen:
                continue
            page_title = sanitize_title(
                str(visit.get("title") or ""),
                bool(policy.get("collectBrowserPageTitle") and policy.get("collectWindowTitle")),
                bool(policy.get("redactSensitiveTerms")),
            )
            event = event_for(
                config,
                str(profile["browser"]),
                page_title,
                visited_at,
                visited_at,
                "browser_history_visit",
                {
                    "quality": "high",
                    "method": f"{profile['engine']}-history",
                    "browser": profile["browser"],
                    "browserProfile": profile["profile"],
                    "browserDomain": domain,
                    "browserUrl": safe_url,
                    "adultContentSignal": adult_signal,
                    "urlQueryCollected": False,
                    "urlFragmentCollected": False,
                    "historyLookbackMinutes": lookback,
                },
                "navegador_adulto" if adult_signal else "navegador",
            )
            if event:
                collected.append(event)
                seen.add(key)
            if len(collected) >= max_events:
                break
    if collected:
        state["seen"] = list(seen)
        state["lastCollectedAt"] = now.isoformat().replace("+00:00", "Z")
        save_browser_state(state)
        log("info", "browser history collected", events=len(collected))
    return collected


def process_name(pid: str) -> str:
    if pid:
        comm = Path("/proc") / pid / "comm"
        if comm.exists():
            value = comm.read_text(encoding="utf-8", errors="ignore").strip()
            if value:
                return value
    return ""


def active_window_xdotool(collect_title: bool) -> tuple[str, str]:
    if not shutil.which("xdotool"):
        return "", ""
    window_id = run_text(["xdotool", "getactivewindow"])
    if not window_id:
        return "", ""
    pid = run_text(["xdotool", "getwindowpid", window_id])
    app = process_name(pid)
    title = run_text(["xdotool", "getwindowname", window_id]) if collect_title else ""
    return app, title


def active_window_gnome(collect_title: bool) -> tuple[str, str]:
    if not shutil.which("gdbus"):
        return "", ""
    script = (
        "global.display.focus_window ? "
        "JSON.stringify({title: global.display.focus_window.get_title(), "
        "wm_class: global.display.focus_window.get_wm_class()}) : '{}'"
    )
    output = run_text(
        [
            "gdbus",
            "call",
            "--session",
            "--dest",
            "org.gnome.Shell",
            "--object-path",
            "/org/gnome/Shell",
            "--method",
            "org.gnome.Shell.Eval",
            script,
        ],
        timeout=2,
    )
    match = re.search(r"\(true,\s*'(.+)'\)", output)
    if not match:
        return "", ""
    raw = match.group(1).encode("utf-8").decode("unicode_escape")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return "", ""
    app = str(payload.get("wm_class") or "").strip()
    title = str(payload.get("title") or "").strip() if collect_title else ""
    return app, title


def active_window_wmctrl(collect_title: bool) -> tuple[str, str]:
    if not (shutil.which("xprop") and shutil.which("wmctrl")):
        return "", ""
    raw_id = run_text(["xprop", "-root", "_NET_ACTIVE_WINDOW"])
    match = re.search(r"window id # (0x[0-9a-fA-F]+)", raw_id)
    if not match:
        return "", ""
    window_id = match.group(1).lower()
    rows = run_text(["wmctrl", "-lp"])
    for row in rows.splitlines():
        parts = row.split(None, 4)
        if len(parts) >= 4 and parts[0].lower() == window_id:
            title = parts[4] if collect_title and len(parts) >= 5 else ""
            return process_name(parts[2]), title
    return "", ""


def process_heuristic(config: dict) -> tuple[str, str]:
    policy = load_policy(config)
    if not policy.get("collectProcessList"):
        return "", ""
    output = run_text(["ps", "-eo", "comm="], timeout=2)
    running = {line.strip().lower() for line in output.splitlines() if line.strip()}
    preferred_apps = [
        ("code", ["code", "codium", "cursor"]),
        ("firefox", ["firefox"]),
        ("chromium", ["chromium", "chrome", "google-chrome", "brave", "brave-browser", "edge", "microsoft-edge"]),
        ("terminal", ["gnome-terminal-", "gnome-terminal", "konsole", "tilix", "alacritty", "xterm"]),
        ("libreoffice", ["libreoffice", "soffice.bin"]),
        ("whatsapp", ["whatsapp", "whatsapp-for-linux"]),
        ("teams", ["teams", "ms-teams"]),
        ("slack", ["slack"]),
        ("zoom", ["zoom"]),
        ("nautilus", ["nautilus"]),
    ]
    for label, candidates in preferred_apps:
        if any(candidate in running for candidate in candidates):
            return label, ""
    return "", ""


def active_window_details(config: dict) -> dict:
    policy = load_policy(config)
    collect_title = bool(policy.get("collectWindowTitle") or config.get("collectWindowTitle"))
    app, title = active_window_xdotool(collect_title)
    method = "xdotool"
    quality = "high" if app else "blocked_by_os"
    if not app:
        app, title = active_window_wmctrl(collect_title)
        method = "wmctrl"
        quality = "high" if app else "blocked_by_os"
    if not app:
        app, title = active_window_gnome(collect_title)
        method = "gnome-shell-dbus"
        quality = "medium" if app else "blocked_by_os"
    if not app:
        app, title = process_heuristic(config)
        method = "process-heuristic"
        quality = "low" if app else "blocked_by_os"
    if not app:
        desktop = os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "Linux"
        app, title = f"{desktop} Desktop", ""
        method = "desktop-fallback"
        quality = "blocked_by_os"
    title = sanitize_title(title, collect_title, bool(policy.get("redactSensitiveTerms")))
    browser_domain, browser_url = sanitize_url(title, bool(policy.get("collectBrowserUrl")), bool(policy.get("collectBrowserDomain")))
    return {
        "app": app,
        "title": title,
        "method": method,
        "quality": quality,
        "category": app_category(app),
        "environment": collection_environment(),
        "browserDomain": browser_domain,
        "browserUrl": browser_url,
    }


def active_window(config: dict) -> tuple[str, str]:
    details = active_window_details(config)
    return str(details["app"]), str(details["title"])


def is_limited_snapshot(snapshot: dict) -> bool:
    return snapshot.get("quality") == "blocked_by_os" or snapshot.get("method") == "desktop-fallback"


def idle_milliseconds() -> int | None:
    if shutil.which("xprintidle"):
        value = run_text(["xprintidle"], timeout=2)
        if value.isdigit():
            return int(value)
    output = run_text(
        [
            "gdbus",
            "call",
            "--session",
            "--dest",
            "org.gnome.Mutter.IdleMonitor",
            "--object-path",
            "/org/gnome/Mutter/IdleMonitor/Core",
            "--method",
            "org.gnome.Mutter.IdleMonitor.GetIdletime",
        ],
        timeout=2,
    )
    match = re.search(r"\(uint64\s+(\d+),\)", output)
    return int(match.group(1)) if match else None


def session_locked_hint() -> bool | None:
    session_id = os.environ.get("XDG_SESSION_ID")
    if not session_id:
        return None
    output = run_text(["loginctl", "show-session", session_id, "-p", "LockedHint", "--value"], timeout=2)
    if output.lower() == "yes":
        return True
    if output.lower() == "no":
        return False
    return None


def uptime_seconds() -> int:
    try:
        return int(float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0]))
    except (OSError, ValueError, IndexError):
        return 0


def local_ip() -> str:
    output = run_text(["hostname", "-I"], timeout=2)
    for item in output.split():
        if "." in item and not item.startswith("127."):
            return item
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("1.1.1.1", 80))
        value = sock.getsockname()[0]
        sock.close()
        return value
    except OSError:
        return ""


def agent_memory_mb() -> int:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return int(usage.ru_maxrss / 1024)


def system_memory_metrics() -> dict:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw_value = line.split(":", 1)
            number = int(raw_value.strip().split()[0])
            values[key] = number
    except (OSError, ValueError, IndexError):
        return {}
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    swap_total = values.get("SwapTotal", 0)
    swap_free = values.get("SwapFree", 0)
    return {
        "memoryTotalMb": int(total / 1024),
        "memoryAvailableMb": int(available / 1024),
        "memoryUsedPercent": round(((total - available) / total) * 100, 1) if total else 0,
        "swapTotalMb": int(swap_total / 1024),
        "swapUsedMb": int((swap_total - swap_free) / 1024),
    }


def disk_metrics(path: str = "/") -> dict:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return {}
    return {
        "diskPath": path,
        "diskTotalGb": round(usage.total / (1024**3), 1),
        "diskFreeGb": round(usage.free / (1024**3), 1),
        "diskUsedPercent": round((usage.used / usage.total) * 100, 1) if usage.total else 0,
    }


def load_metrics() -> dict:
    try:
        load1, load5, load15 = os.getloadavg()
    except OSError:
        return {}
    return {"load1": round(load1, 2), "load5": round(load5, 2), "load15": round(load15, 2), "cpuCount": os.cpu_count() or 0}


def top_processes(limit: int = 5) -> list[dict]:
    output = run_text(["ps", "-eo", "comm=,%cpu=,%mem=", "--sort=-%cpu"], timeout=2)
    rows: list[dict] = []
    for line in output.splitlines():
        if len(rows) >= limit:
            break
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            cpu = float(parts[-2])
            mem = float(parts[-1])
        except ValueError:
            continue
        name = " ".join(parts[:-2])[:80]
        if name:
            rows.append({"name": name, "cpuPercent": cpu, "memoryPercent": mem})
    return rows


def machine_health_metrics(policy: dict | None = None) -> dict:
    metrics = {
        **load_metrics(),
        **system_memory_metrics(),
        **disk_metrics("/"),
    }
    if policy and policy.get("collectProcessList"):
        metrics["topProcesses"] = top_processes()
    return metrics


def append_event(event: dict, max_queue_size: int | None = None) -> None:
    if max_queue_size and queue_depth() >= max_queue_size:
        log("warning", "offline queue limit reached; dropping oldest event", maxOfflineQueueSize=max_queue_size)
        drop_events(1)
    queue_path().parent.mkdir(parents=True, exist_ok=True)
    with queue_path().open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_events(limit: int = 200) -> list[dict]:
    if not queue_path().exists():
        return []
    events: list[dict] = []
    with queue_path().open("r", encoding="utf-8") as file:
        for line in file:
            if len(events) >= limit:
                break
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("appName"):
                events.append(payload)
    return events


def drop_events(count: int) -> None:
    if not queue_path().exists():
        return
    lines = queue_path().read_text(encoding="utf-8").splitlines()
    remaining = lines[max(count, 0) :]
    queue_path().parent.mkdir(parents=True, exist_ok=True)
    queue_path().write_text(("\n".join(remaining) + "\n") if remaining else "", encoding="utf-8")


def queue_depth() -> int:
    if not queue_path().exists():
        return 0
    return sum(1 for _ in queue_path().open("r", encoding="utf-8"))


def post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": f"VulcanLinuxAgent/{VERSION}"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            data = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    if not data:
        return {}
    return json.loads(data)


def enroll(config: dict) -> None:
    policy = load_policy(config)
    response = post_json(
        f"{config['backendUrl']}/agent/enroll",
        {
            "tenantId": config["tenantId"],
            "enrollmentToken": config["enrollmentToken"],
            "hostname": config["hostname"],
            "osUser": config["osUser"],
            "osVersion": config["osVersion"],
            "deviceId": config.get("deviceId"),
            "machineFingerprint": config["machineFingerprint"],
            "agentVersion": VERSION,
            "linkedUser": config.get("linkedUser"),
            "membershipId": config.get("membershipId") or None,
            "roleLevel": config.get("roleLevel"),
            "department": config.get("department"),
            "note": "linux-agent",
        },
        timeout=int(policy.get("httpTimeoutSeconds", 30)),
    )
    if response.get("deviceId") and response["deviceId"] != config.get("deviceId"):
        config["deviceId"] = response["deviceId"]
        save_config(config)
    log("info", "enrolled", deviceId=config.get("deviceId"))


def heartbeat(config: dict, status: str = "online", last_error: str = "", metadata: dict | None = None) -> None:
    policy = load_policy(config)
    post_json(
        f"{config['backendUrl']}/agent/heartbeat",
        {
            "tenantId": config["tenantId"],
            "enrollmentToken": config["enrollmentToken"],
            "deviceId": config.get("deviceId"),
            "machineFingerprint": config["machineFingerprint"],
            "hostname": config["hostname"],
            "agentVersion": VERSION,
            "status": status,
            "queueDepth": queue_depth(),
            "lastError": last_error,
            "metadata": {
                "localIp": local_ip(),
                "uptimeSeconds": uptime_seconds(),
                "agentMemoryMb": agent_memory_mb(),
                "collectionQuality": (metadata or {}).get("collectionQuality"),
                "collectionMethod": (metadata or {}).get("collectionMethod"),
                "collectionEnvironment": collection_environment(),
                "policy": {
                    "collectWindowTitle": bool(policy.get("collectWindowTitle")),
                    "collectIdleTime": bool(policy.get("collectIdleTime")),
                    "collectBrowserDomain": bool(policy.get("collectBrowserDomain")),
                    "collectBrowserUrl": bool(policy.get("collectBrowserUrl")),
                    "collectBrowserHistory": bool(policy.get("collectBrowserHistory")),
                    "collectProcessList": bool(policy.get("collectProcessList")),
                    "privacyMode": policy.get("privacyMode"),
                },
                "machine": machine_health_metrics(policy),
                **(metadata or {}),
            },
        },
        timeout=int(policy.get("httpTimeoutSeconds", 30)),
    )


def sync(config: dict) -> None:
    policy = load_policy(config)
    events = read_events(int(policy.get("syncBatchSize", 100)))
    if not events:
        return
    response = post_json(
        f"{config['backendUrl']}/agent/sync",
        {
            "tenantId": config["tenantId"],
            "enrollmentToken": config["enrollmentToken"],
            "deviceId": config.get("deviceId"),
            "membershipId": config.get("membershipId") or None,
            "machineFingerprint": config["machineFingerprint"],
            "hostname": config["hostname"],
            "events": events,
        },
        timeout=int(policy.get("httpTimeoutSeconds", 30)),
    )
    stored = int(response.get("stored") or len(events))
    drop_events(stored)
    log("info", "synced", stored=stored)


def event_for(
    config: dict,
    app: str,
    title: str,
    started_at: datetime,
    ended_at: datetime,
    event_type: str = "app_focus_ended",
    metadata: dict | None = None,
    category: str | None = None,
) -> dict | None:
    duration = max(0, int((ended_at - started_at).total_seconds()))
    instant_events = {
        "context_switch",
        "idle_started",
        "session_locked",
        "session_unlocked",
        "user_logged_in",
        "user_logged_out",
        "machine_sleep",
        "machine_resume",
        "heartbeat",
        "sync_status",
        "collection_quality",
        "agent_error",
        "agent_health",
        "browser_history_visit",
    }
    if duration < 1 and event_type not in instant_events:
        return None
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "appName": app,
        "windowTitle": title,
        "category": category or app_category(app),
        "startedAt": started_at.isoformat().replace("+00:00", "Z"),
        "endedAt": ended_at.isoformat().replace("+00:00", "Z"),
        "durationSeconds": duration,
        "osUser": config.get("osUser"),
        "metadata": {
            **(metadata or {}),
            "collector": "linux-session",
            "agentVersion": VERSION,
            "privacy": {
                "keystrokes": False,
                "screenshots": False,
                "clipboard": False,
                "audio": False,
                "webcam": False,
            },
        },
    }


def run_loop() -> None:
    config = load_config()
    policy = load_policy(config)
    try:
        enroll(config)
    except Exception as exc:
        log("warning", f"enrollment failed: {exc}")

    first_seen = utc_now()
    append_event(
        event_for(
            config,
            "Vulcan Agent",
            "",
            first_seen,
            first_seen,
            "user_logged_in",
            {"hostname": config.get("hostname"), "localIp": local_ip(), "uptimeSeconds": uptime_seconds()},
            "sistema",
        ),
        policy["maxOfflineQueueSize"],
    )

    last_snapshot = active_window_details(config)
    last_app, last_title = str(last_snapshot["app"]), str(last_snapshot["title"])
    started_at = utc_now()
    last_heartbeat = 0.0
    last_sync = 0.0
    last_health = 0.0
    last_browser_history = 0.0
    last_error = ""
    last_quality = str(last_snapshot["quality"])
    last_locked = session_locked_hint()
    idle_started_at: datetime | None = None
    last_loop_wall = time.time()
    max_event_seconds = 60

    while True:
        now = utc_now()
        policy = load_policy(config)
        snapshot = active_window_details(config)
        app, title = str(snapshot["app"]), str(snapshot["title"])
        changed = app != last_app or title != last_title
        expired = int((now - started_at).total_seconds()) >= max_event_seconds

        wall_now = time.time()
        if wall_now - last_loop_wall > 90 and policy.get("collectSessionEvents"):
            event = event_for(config, "Sistema", "", now, now, "machine_resume", {"gapSeconds": int(wall_now - last_loop_wall)}, "sistema")
            if event:
                append_event(event, policy["maxOfflineQueueSize"])
        last_loop_wall = wall_now

        if policy.get("collectIdleTime"):
            idle_ms = idle_milliseconds()
            idle_seconds = int(idle_ms / 1000) if idle_ms is not None else None
            is_idle = idle_seconds is not None and idle_seconds >= int(policy["idleThresholdSeconds"])
            if is_idle and idle_started_at is None:
                idle_started_at = now
                event = event_for(config, "Sistema", "", now, now, "idle_started", {"idleSeconds": idle_seconds, "quality": snapshot["quality"]}, "sistema")
                if event:
                    append_event(event, policy["maxOfflineQueueSize"])
            if not is_idle and idle_started_at is not None:
                event = event_for(config, "Sistema", "", idle_started_at, now, "idle_ended", {"quality": snapshot["quality"]}, "sistema")
                if event:
                    append_event(event, policy["maxOfflineQueueSize"])
                idle_started_at = None

        if policy.get("collectSessionEvents"):
            locked = session_locked_hint()
            if locked is not None and last_locked is not None and locked != last_locked:
                event = event_for(config, "Sistema", "", now, now, "session_locked" if locked else "session_unlocked", {"quality": snapshot["quality"]}, "sistema")
                if event:
                    append_event(event, policy["maxOfflineQueueSize"])
            if locked is not None:
                last_locked = locked

        if str(snapshot["quality"]) != last_quality:
            event = event_for(
                config,
                "Vulcan Agent",
                "",
                now,
                now,
                "collection_quality",
                {"quality": snapshot["quality"], "method": snapshot["method"], "environment": snapshot["environment"]},
                "sistema",
            )
            if event:
                append_event(event, policy["maxOfflineQueueSize"])
            last_quality = str(snapshot["quality"])

        if changed or expired:
            last_limited = is_limited_snapshot(last_snapshot)
            event = event_for(
                config,
                "Vulcan Agent" if last_limited else last_app,
                "" if last_limited else last_title,
                started_at,
                now,
                "collection_limited" if last_limited else "app_focus_ended",
                {
                    "quality": last_snapshot["quality"],
                    "method": last_snapshot["method"],
                    "environment": last_snapshot["environment"],
                    "browserDomain": "" if last_limited else last_snapshot["browserDomain"],
                    "browserUrl": "" if last_limited else last_snapshot["browserUrl"],
                    "unidentifiedApp": last_app if last_limited else "",
                },
                "sistema" if last_limited else str(last_snapshot["category"]),
            )
            if event:
                append_event(event, policy["maxOfflineQueueSize"])
            if changed and not last_limited and not is_limited_snapshot(snapshot):
                switch = event_for(
                    config,
                    "Troca de contexto",
                    "",
                    now,
                    now,
                    "context_switch",
                    {"fromApp": last_app, "toApp": app, "quality": snapshot["quality"]},
                    "sistema",
                )
                if switch:
                    append_event(switch, policy["maxOfflineQueueSize"])
            last_app, last_title = app, title
            last_snapshot = snapshot
            started_at = now

        monotonic = time.monotonic()
        if policy.get("collectBrowserHistory") and monotonic - last_browser_history >= int(policy.get("browserHistoryIntervalSeconds", 300)):
            try:
                for event in collect_browser_history_events(config, policy, now):
                    append_event(event, policy["maxOfflineQueueSize"])
            except Exception as exc:
                last_error = str(exc)
                event = event_for(config, "Vulcan Agent", "", now, now, "agent_error", {"error": last_error, "scope": "browser_history"}, "sistema")
                if event:
                    append_event(event, policy["maxOfflineQueueSize"])
                log("warning", f"browser history collection failed: {exc}")
            last_browser_history = monotonic

        if policy.get("collectSystemMetrics") and monotonic - last_health >= 60:
            event = event_for(
                config,
                "Vulcan Agent",
                "",
                now,
                now,
                "agent_health",
                {
                    "agentMemoryMb": agent_memory_mb(),
                    "uptimeSeconds": uptime_seconds(),
                    "queueDepth": queue_depth(),
                    "localIp": local_ip(),
                    "quality": snapshot["quality"],
                    "machine": machine_health_metrics(policy),
                },
                "sistema",
            )
            if event:
                append_event(event, policy["maxOfflineQueueSize"])
            last_health = monotonic

        if monotonic - last_sync >= int(policy.get("syncIntervalSeconds", config.get("syncIntervalSeconds", 30))):
            try:
                sync(config)
                last_error = ""
            except Exception as exc:
                last_error = str(exc)
                event = event_for(config, "Vulcan Agent", "", now, now, "agent_error", {"error": last_error}, "sistema")
                if event:
                    append_event(event, policy["maxOfflineQueueSize"])
                log("warning", f"sync failed: {exc}")
            last_sync = monotonic

        if monotonic - last_heartbeat >= int(policy.get("heartbeatIntervalSeconds", config.get("heartbeatIntervalSeconds", 60))):
            try:
                heartbeat(config, "online", last_error, {"collectionQuality": snapshot["quality"], "collectionMethod": snapshot["method"]})
            except Exception as exc:
                last_error = str(exc)
                log("warning", f"heartbeat failed: {exc}")
            last_heartbeat = monotonic

        time.sleep(2)


def create_config(args: argparse.Namespace) -> None:
    config = default_config(args)
    save_config(config)
    save_policy(default_policy(args), Path(config["policyPath"]))
    (data_dir() / "queue").mkdir(parents=True, exist_ok=True)
    (data_dir() / "logs").mkdir(parents=True, exist_ok=True)
    print(config_path())


def print_status() -> None:
    config = load_config()
    policy = load_policy(config)
    print(f"Vulcan Linux Agent {VERSION}")
    print(f"Config: {config_path()}")
    print(f"Policy: {config.get('policyPath') or policy_path()}")
    print(f"Backend: {config.get('backendUrl')}")
    print(f"Tenant: {config.get('tenantId')}")
    print(f"DeviceId: {config.get('deviceId')}")
    print(f"LinkedUser: {config.get('linkedUser')}")
    print(f"MembershipId: {config.get('membershipId') or '(not linked)'}")
    print(f"RoleLevel: {config.get('roleLevel')}")
    print(f"Department: {config.get('department')}")
    print(f"CollectionQuality: {active_window_details(config).get('quality')}")
    print(f"CollectionMethod: {active_window_details(config).get('method')}")
    print(f"CollectWindowTitle: {policy.get('collectWindowTitle')}")
    print(f"CollectIdleTime: {policy.get('collectIdleTime')}")
    print(f"CollectBrowserDomain: {policy.get('collectBrowserDomain')}")
    print(f"CollectBrowserUrl: {policy.get('collectBrowserUrl')}")
    print(f"CollectBrowserHistory: {policy.get('collectBrowserHistory')}")
    print(f"CollectProcessList: {policy.get('collectProcessList')}")
    print(f"PrivacyMode: {policy.get('privacyMode')}")
    print(f"MachineHealth: {json.dumps(machine_health_metrics(policy), ensure_ascii=False)}")
    print(f"SyncBatchSize: {policy.get('syncBatchSize')}")
    print(f"HttpTimeoutSeconds: {policy.get('httpTimeoutSeconds')}")
    print(f"QueueDepth: {queue_depth()}")
    print(f"Log: {log_path()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Vulcan Linux Agent")
    sub = parser.add_subparsers(dest="command", required=True)

    config_cmd = sub.add_parser("write-config")
    config_cmd.add_argument("--tenant-id")
    config_cmd.add_argument("--backend-url")
    config_cmd.add_argument("--enrollment-token")
    config_cmd.add_argument("--linked-user")
    config_cmd.add_argument("--membership-id")
    config_cmd.add_argument("--role-level")
    config_cmd.add_argument("--department")
    config_cmd.add_argument("--collect-window-title", action="store_true")
    config_cmd.add_argument("--collect-browser-domain", action="store_true")
    config_cmd.add_argument("--collect-browser-url", action="store_true")
    config_cmd.add_argument("--collect-browser-history", action="store_true")
    config_cmd.add_argument("--collect-process-list", action="store_true")
    config_cmd.add_argument("--corporate-monitoring", action="store_true")
    config_cmd.add_argument("--heartbeat-interval", type=int)
    config_cmd.add_argument("--sync-interval", type=int)

    sub.add_parser("run")
    sub.add_parser("enroll")
    sub.add_parser("heartbeat")
    sub.add_parser("sync")
    sub.add_parser("status")

    args = parser.parse_args()
    if args.command == "write-config":
        create_config(args)
    elif args.command == "run":
        run_loop()
    elif args.command == "enroll":
        enroll(load_config())
    elif args.command == "heartbeat":
        heartbeat(load_config())
    elif args.command == "sync":
        sync(load_config())
    elif args.command == "status":
        print_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
