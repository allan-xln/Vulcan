from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TENANT_ID = "00000000-0000-0000-0000-000000000301"
DEFAULT_PACKAGE_URL = "http://192.168.200.160:8099/VulcanAgent-Windows-x64.zip"
DEFAULT_BACKEND_URL = "http://192.168.200.160:3001"
DEFAULT_TOKEN = "vulcan-local-enrollment-token"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def load_targets(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    targets = payload.get("targets", [])
    return [
        target for target in targets
        if target.get("windowsLikely") and target.get("ports", {}).get("5985")
    ]


def install_script(package_url: str, backend_url: str, token: str) -> str:
    return rf"""
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$packageUrl = "{package_url}"
$tenantId = "{TENANT_ID}"
$backendUrl = "{backend_url}"
$token = "{token}"
$root = Join-Path $env:ProgramData "Vulcan\Deploy"
$zip = Join-Path $root "VulcanAgent-Windows-x64.zip"
$extract = Join-Path $root "package"
New-Item -ItemType Directory -Path $root -Force | Out-Null
if (Test-Path $extract) {{ Remove-Item -Recurse -Force $extract }}
New-Item -ItemType Directory -Path $extract -Force | Out-Null
Invoke-WebRequest -Uri $packageUrl -OutFile $zip -UseBasicParsing
Expand-Archive -Path $zip -DestinationPath $extract -Force
$installer = Join-Path $extract "install-gpo.cmd"
if (-not (Test-Path $installer)) {{ throw "install-gpo.cmd not found after extraction" }}
& $installer -TenantId $tenantId -BackendUrl $backendUrl -EnrollmentToken $token -LinkedUser "$env:USERDOMAIN\$env:USERNAME" -RoleLevel "Operador" -Department "Operacoes" -CorporateMonitoring
$service = Get-Service -Name VulcanAgent -ErrorAction Stop
$status = & (Join-Path $extract "status.ps1") 2>&1 | Out-String
[pscustomobject]@{{
  ok = $true
  computer = $env:COMPUTERNAME
  domain = (Get-CimInstance Win32_ComputerSystem).Domain
  service = $service.Status.ToString()
  package = $packageUrl
  backend = $backendUrl
  statusOutput = $status.Trim()
}} | ConvertTo-Json -Compress
"""


def inspect_script() -> str:
    return """
$ErrorActionPreference = "Stop"
$service = Get-Service -Name VulcanAgent -ErrorAction SilentlyContinue
$config = "C:\\ProgramData\\Vulcan\\Agent\\config\\agent.json"
[pscustomobject]@{
  serviceExists = [bool]$service
  serviceStatus = if ($service) { $service.Status.ToString() } else { $null }
  configExists = Test-Path $config
  config = if (Test-Path $config) { Get-Content $config -Raw | ConvertFrom-Json } else { $null }
} | ConvertTo-Json -Depth 8 -Compress
"""


def run_target(target: dict[str, Any], username: str, password: str, package_url: str, backend_url: str, token: str, confirm: bool) -> dict[str, Any]:
    import winrm  # type: ignore

    host = target["ip"]
    result: dict[str, Any] = {
        "ip": host,
        "hostname": target.get("hostname"),
        "attempted": confirm,
        "ok": False,
        "startedAt": datetime.now(timezone.utc).isoformat(),
    }
    try:
        session = winrm.Session(f"http://{host}:5985/wsman", auth=(username, password), transport="ntlm")
        if confirm:
            response = session.run_ps(install_script(package_url, backend_url, token))
        else:
            response = session.run_ps(inspect_script())
        result["statusCode"] = response.status_code
        result["stdout"] = response.std_out.decode("utf-8", errors="replace")[-4000:]
        result["stderr"] = response.std_err.decode("utf-8", errors="replace")[-2000:]
        result["ok"] = response.status_code == 0
    except Exception as exc:  # noqa: BLE001 - deployment report
        result["error"] = str(exc)
    result["finishedAt"] = datetime.now(timezone.utc).isoformat()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy autorizado do agente Windows ERS via WinRM.")
    parser.add_argument("--discovery", default=".runtime/ers-windows-discovery.json")
    parser.add_argument("--out", default=".runtime/ers-agent-deploy-report.json")
    parser.add_argument("--package-url", default=DEFAULT_PACKAGE_URL)
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    parser.add_argument("--token", default=DEFAULT_TOKEN)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--confirm-deploy", action="store_true")
    args = parser.parse_args()

    username = require_env("ERS_WINRM_USER")
    password = require_env("ERS_WINRM_PASSWORD")
    targets = load_targets(Path(args.discovery))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(executor.map(
            lambda target: run_target(target, username, password, args.package_url, args.backend_url, args.token, args.confirm_deploy),
            targets,
        ))
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "confirmDeploy": args.confirm_deploy,
        "packageUrl": args.package_url,
        "backendUrl": args.backend_url,
        "summary": {
            "targets": len(targets),
            "attempted": sum(1 for item in results if item["attempted"]),
            "ok": sum(1 for item in results if item["ok"]),
            "failed": sum(1 for item in results if not item["ok"]),
        },
        "results": results,
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    print(f"report={output}")
    if args.confirm_deploy and report["summary"]["failed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
