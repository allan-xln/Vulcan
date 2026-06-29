from __future__ import annotations

import argparse
import concurrent.futures
import ipaddress
import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PORTS = (445, 3389, 5985)


def tcp_open(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def ping(host: str, timeout_seconds: int) -> bool:
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout_seconds), host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except OSError:
        return False


def reverse_dns(host: str) -> str | None:
    try:
        return socket.gethostbyaddr(host)[0]
    except OSError:
        return None


def winrm_identity(host: str, username: str | None, password: str | None) -> dict[str, Any] | None:
    if not username or not password:
        return None
    try:
        import winrm  # type: ignore
    except ImportError:
        return {"winrmCredentialValid": None, "winrmError": "pywinrm not installed"}
    try:
        session = winrm.Session(f"http://{host}:5985/wsman", auth=(username, password), transport="ntlm")
        result = session.run_ps(
            """
            $ProgressPreference = 'SilentlyContinue'
            [pscustomobject]@{
              ComputerName = $env:COMPUTERNAME
              Domain = (Get-CimInstance Win32_ComputerSystem).Domain
              OS = (Get-CimInstance Win32_OperatingSystem).Caption
              Version = (Get-CimInstance Win32_OperatingSystem).Version
              VulcanService = (Get-Service -Name VulcanAgent -ErrorAction SilentlyContinue).Status
            } | ConvertTo-Json -Compress
            """
        )
        if result.status_code != 0:
            return {"winrmCredentialValid": False, "winrmError": result.std_err.decode("utf-8", errors="replace")[:500]}
        payload = json.loads(result.std_out.decode("utf-8", errors="replace"))
        return {"winrmCredentialValid": True, **payload}
    except Exception as exc:  # noqa: BLE001 - diagnostic script
        return {"winrmCredentialValid": False, "winrmError": str(exc)[:500]}


def inspect_host(host: str, timeout: float, winrm_user: str | None, winrm_password: str | None) -> dict[str, Any]:
    open_ports = {str(port): tcp_open(host, port, timeout) for port in DEFAULT_PORTS}
    result: dict[str, Any] = {
        "ip": host,
        "hostname": reverse_dns(host),
        "ping": ping(host, max(1, int(timeout))),
        "ports": open_ports,
        "windowsLikely": open_ports["445"] or open_ports["3389"] or open_ports["5985"],
        "deployEligible": False,
        "reason": "winrm closed",
    }
    if open_ports["5985"]:
        identity = winrm_identity(host, winrm_user, winrm_password)
        if identity:
            result.update(identity)
        result["deployEligible"] = bool(result.get("winrmCredentialValid"))
        result["reason"] = "ready_for_pilot" if result["deployEligible"] else "winrm credential not validated"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Descoberta controlada de alvos Windows ERS. Nao instala agente.")
    parser.add_argument("--network", default="192.168.200.0/24", help="CIDR autorizado para varredura LAN.")
    parser.add_argument("--timeout", type=float, default=1.2)
    parser.add_argument("--workers", type=int, default=64)
    parser.add_argument("--out", default=".runtime/ers-windows-discovery.json")
    args = parser.parse_args()

    network = ipaddress.ip_network(args.network, strict=False)
    if not network.is_private:
        raise SystemExit("Only private LAN ranges are allowed")
    if network.num_addresses > 1024:
        raise SystemExit("Refusing to scan more than 1024 addresses")

    username = os.getenv("ERS_WINRM_USER")
    password = os.getenv("ERS_WINRM_PASSWORD")
    hosts = [str(host) for host in network.hosts()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        rows = list(executor.map(lambda host: inspect_host(host, args.timeout, username, password), hosts))

    relevant = [row for row in rows if row["ping"] or row["windowsLikely"]]
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "network": str(network),
        "installAttempted": False,
        "credentialsProvided": bool(username and password),
        "summary": {
            "hostsScanned": len(hosts),
            "hostsRelevant": len(relevant),
            "windowsLikely": sum(1 for row in relevant if row["windowsLikely"]),
            "winrmOpen": sum(1 for row in relevant if row["ports"].get("5985")),
            "deployEligible": sum(1 for row in relevant if row["deployEligible"]),
        },
        "targets": relevant,
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    print(f"report={output}")


if __name__ == "__main__":
    main()
