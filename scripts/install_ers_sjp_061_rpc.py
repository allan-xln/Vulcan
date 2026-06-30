from __future__ import annotations

import argparse
import os
import socket
import subprocess
import tempfile
import time
from pathlib import Path


DEFAULT_HOST = "192.168.200.81"
DEFAULT_NAME = "ERS-SJP-061"
DEFAULT_PACKAGE_SCRIPT = "http://192.168.200.160:8099/ers-gpo-startup-install.ps1"
TEMP_SERVICE = "VulcanBootstrap"


def tcp_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def run(cmd: list[str], timeout: int = 45) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def nmb_name(host: str) -> str:
    result = run(["nmblookup", "-A", host], timeout=8)
    return f"{result.stdout}\n{result.stderr}"


def samba_auth_file(username: str, password: str, domain: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", delete=False, prefix="vulcan-samba-", suffix=".auth")
    path = Path(handle.name)
    handle.write(f"username = {username}\n")
    handle.write(f"password = {password}\n")
    handle.write(f"domain = {domain}\n")
    handle.close()
    path.chmod(0o600)
    return path


def rpc_base(host: str, auth_file: Path) -> list[str]:
    return ["net", "rpc", "-S", host, "-I", host, "-A", str(auth_file)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Instala o VulcanAgent no host ERS-SJP-061 via RPC/SCM.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--expected-name", default=DEFAULT_NAME)
    parser.add_argument("--domain", default=os.getenv("ERS_ADMIN_DOMAIN", "ERSTRANSPORTES"))
    parser.add_argument("--user", default=os.getenv("ERS_ADMIN_USER") or os.getenv("ERS_WINRM_USER"))
    parser.add_argument("--password", default=os.getenv("ERS_ADMIN_PASSWORD") or os.getenv("ERS_WINRM_PASSWORD"))
    parser.add_argument("--script-url", default=DEFAULT_PACKAGE_SCRIPT)
    parser.add_argument("--wait", type=int, default=0, help="Segundos para aguardar a maquina voltar na rede.")
    args = parser.parse_args()

    if not args.user or not args.password:
        raise SystemExit("Defina ERS_ADMIN_USER/ERS_ADMIN_PASSWORD ou ERS_WINRM_USER/ERS_WINRM_PASSWORD.")

    deadline = time.monotonic() + max(0, args.wait)
    while True:
        if tcp_open(args.host, 445):
            break
        if time.monotonic() >= deadline:
            raise SystemExit(f"{args.host} offline ou porta 445 fechada.")
        print(f"{args.host} offline, aguardando...")
        time.sleep(10)

    names = nmb_name(args.host)
    if args.expected_name.upper() not in names.upper():
        raise SystemExit(f"Host respondeu, mas NetBIOS nao confirmou {args.expected_name}.\n{names}")

    auth_file = samba_auth_file(args.user, args.password, args.domain)
    try:
        script = (
            "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "
            "\"$ErrorActionPreference='Stop'; "
            "$root=Join-Path $env:ProgramData 'Vulcan\\Deploy'; "
            "New-Item -ItemType Directory -Path $root -Force | Out-Null; "
            "$script=Join-Path $root 'ers-gpo-startup-install.ps1'; "
            f"Invoke-WebRequest -Uri '{args.script_url}' -OutFile $script -UseBasicParsing; "
            "powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script\""
        )
        create = rpc_base(args.host, auth_file) + [
            "service",
            "create",
            TEMP_SERVICE,
            "Vulcan Bootstrap",
            script,
        ]
        start = rpc_base(args.host, auth_file) + ["service", "start", TEMP_SERVICE]
        delete = rpc_base(args.host, auth_file) + ["service", "delete", TEMP_SERVICE]

        for cleanup in (["service", "stop", TEMP_SERVICE], ["service", "delete", TEMP_SERVICE]):
            run(rpc_base(args.host, auth_file) + cleanup, timeout=15)

        result = run(create, timeout=45)
        print(result.stdout.strip())
        if result.returncode != 0:
            raise SystemExit(result.stderr.strip() or result.stdout.strip() or "Falha ao criar servico temporario.")

        result = run(start, timeout=45)
        print(result.stdout.strip())
        if result.returncode != 0:
            print(result.stderr.strip())

        time.sleep(8)
        run(delete, timeout=30)

        status = run(rpc_base(args.host, auth_file) + ["service", "status", "VulcanAgent"], timeout=30)
        print(status.stdout.strip() or status.stderr.strip())
        if status.returncode != 0:
            raise SystemExit("Bootstrap disparado, mas ainda nao consegui validar o servico VulcanAgent.")
    finally:
        try:
            auth_file.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    main()
