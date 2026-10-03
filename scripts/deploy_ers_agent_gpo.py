from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path


GPO_NAME = "Vulcan Agent - Estacoes ERS"
DC_URL = "http://192.168.200.4:5985/wsman"


def powershell_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def password_from_environment() -> str:
    password_file = os.getenv("ERS_WINRM_PASSWORD_FILE")
    if password_file:
        path = Path(password_file).expanduser()
        if path.stat().st_mode & 0o077:
            raise SystemExit("ERS_WINRM_PASSWORD_FILE must not be accessible by group or others")
        return path.read_text(encoding="utf-8").strip()
    if password := os.getenv("ERS_WINRM_PASSWORD"):
        return password
    raise SystemExit("Set ERS_WINRM_PASSWORD_FILE to a protected credential file")


def run_ps(session, script: str) -> str:
    response = session.run_ps(script)
    if response.status_code != 0:
        detail = response.std_err.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail[-1200:] or f"PowerShell returned {response.status_code}")
    return response.std_out.decode("utf-8", errors="replace").strip()


def upload_file(session, source: Path, destination: str) -> None:
    run_ps(session, f"[IO.File]::WriteAllBytes({powershell_literal(destination)}, [byte[]]@())")
    with source.open("rb") as stream:
        while chunk := stream.read(192 * 1024):
            encoded = base64.b64encode(chunk).decode("ascii")
            run_ps(
                session,
                "$bytes=[Convert]::FromBase64String("
                + powershell_literal(encoded)
                + ");$file=[IO.File]::Open("
                + powershell_literal(destination)
                + ",[IO.FileMode]::Append,[IO.FileAccess]::Write,[IO.FileShare]::None);"
                + "try{$file.Write($bytes,0,$bytes.Length)}finally{$file.Dispose()}",
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audita e, com confirmação explícita, publica o Vulcan Agent por GPO."
    )
    parser.add_argument("--dc-url", default=DC_URL)
    parser.add_argument("--username", default=os.getenv("ERS_WINRM_USER", ""))
    parser.add_argument(
        "--agent",
        type=Path,
        default=Path("frontend/web/public/agent-v2/VulcanAgentUser.exe"),
    )
    parser.add_argument(
        "--logon-script",
        type=Path,
        default=Path("agentes/agent/packaging/windows/ers-gpo-user-logon.ps1"),
    )
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--token-ttl-hours", type=int, default=36)
    parser.add_argument("--confirm-deploy", action="store_true")
    args = parser.parse_args()

    if not args.username:
        raise SystemExit("Set ERS_WINRM_USER or pass --username")
    if not 1 <= args.token_ttl_hours <= 72:
        raise SystemExit("--token-ttl-hours must be between 1 and 72")

    try:
        import winrm  # type: ignore
    except ImportError as exc:
        raise SystemExit("Install pywinrm in the project virtual environment") from exc

    session = winrm.Session(
        args.dc_url,
        auth=(args.username, password_from_environment()),
        transport="ntlm",
    )
    inspection = json.loads(
        run_ps(
            session,
            r"""
$ErrorActionPreference='Stop'
Import-Module ActiveDirectory
Import-Module GroupPolicy
$domain=Get-ADDomain
$computers=Get-ADComputer -Filter * -Properties OperatingSystem,Enabled
[pscustomobject]@{
  computerName=$env:COMPUTERNAME
  domain=$domain.DNSRoot
  domainDn=$domain.DistinguishedName
  enabledWorkstations=@($computers | Where-Object {$_.Enabled -and $_.OperatingSystem -notlike '*Server*'}).Count
  enabledServers=@($computers | Where-Object {$_.Enabled -and $_.OperatingSystem -like '*Server*'}).Count
  existingGpo=[bool](Get-GPO -Name 'Vulcan Agent - Estacoes ERS' -ErrorAction SilentlyContinue)
} | ConvertTo-Json -Compress
""",
        )
    )
    print(json.dumps({"inspection": inspection, "mutationRequested": args.confirm_deploy}, ensure_ascii=False))
    if not args.confirm_deploy:
        return

    if not args.token_file:
        raise SystemExit("--token-file is required with --confirm-deploy")
    for required in (args.agent, args.logon_script, args.token_file):
        if not required.is_file():
            raise SystemExit(f"Missing required deployment file: {required}")

    staging = rf"C:\Windows\Temp\Vulcan-GPO-{uuid.uuid4().hex}"
    run_ps(session, f"New-Item -ItemType Directory -Force -Path {powershell_literal(staging)} | Out-Null")
    try:
        destinations = {
            args.agent: staging + r"\VulcanAgentUser.exe",
            args.logon_script: staging + r"\ers-gpo-user-logon.ps1",
            args.token_file: staging + r"\enrollment.token",
        }
        for source, destination in destinations.items():
            upload_file(session, source, destination)

        expected_hash = hashlib.sha256(args.agent.read_bytes()).hexdigest().upper()
        deployment = json.loads(
            run_ps(
                session,
                rf"""
$ErrorActionPreference='Stop'
Import-Module ActiveDirectory
Import-Module GroupPolicy
$domain=Get-ADDomain
$domainName=$domain.DNSRoot
$destination=Join-Path $env:WINDIR "SYSVOL\sysvol\$domainName\scripts\Vulcan"
New-Item -ItemType Directory -Force -Path $destination | Out-Null
Copy-Item -LiteralPath {powershell_literal(destinations[args.agent])} -Destination (Join-Path $destination 'VulcanAgentUser.exe') -Force
Copy-Item -LiteralPath {powershell_literal(destinations[args.logon_script])} -Destination (Join-Path $destination 'ers-gpo-user-logon.ps1') -Force
Copy-Item -LiteralPath {powershell_literal(destinations[args.token_file])} -Destination (Join-Path $destination 'enrollment.token') -Force
$actualHash=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $destination 'VulcanAgentUser.exe')).Hash
if($actualHash -ne {powershell_literal(expected_hash)}){{throw 'Agent checksum mismatch after SYSVOL copy'}}

$gpo=Get-GPO -Name {powershell_literal(GPO_NAME)} -ErrorAction SilentlyContinue
if(-not $gpo){{$gpo=New-GPO -Name {powershell_literal(GPO_NAME)} -Comment 'Vulcan Agent v2 por usuario; coleta autorizada de saude, inventario, aplicativo em foco e ociosidade, sem conteudo privado.'}}
$command='powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "\\'+$domainName+'\SYSVOL\'+$domainName+'\scripts\Vulcan\ers-gpo-user-logon.ps1"'
Set-GPRegistryValue -Name {powershell_literal(GPO_NAME)} -Key 'HKLM\Software\Microsoft\Windows\CurrentVersion\Run' -ValueName 'VulcanAgent' -Type String -Value $command | Out-Null
$linked=@((Get-GPInheritance -Target $domain.DistinguishedName).GpoLinks | Where-Object {{$_.DisplayName -eq {powershell_literal(GPO_NAME)}}}).Count -gt 0
if(-not $linked){{New-GPLink -Name {powershell_literal(GPO_NAME)} -Target $domain.DistinguishedName -LinkEnabled Yes | Out-Null}}

$tokenPath=Join-Path $destination 'enrollment.token'
$taskName='Vulcan - remover token temporario da GPO'
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -Command "Remove-Item -LiteralPath '''+$tokenPath+''' -Force -ErrorAction SilentlyContinue"')
$trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddHours({args.token_ttl_hours})
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -User 'SYSTEM' -RunLevel Highest -Force | Out-Null

[pscustomobject]@{{
  gpoName=$gpo.DisplayName
  gpoId=$gpo.Id.Guid
  domain=$domainName
  linked=$true
  agentSha256=$actualHash
  tokenCleanupAt=(Get-Date).AddHours({args.token_ttl_hours}).ToString('o')
}} | ConvertTo-Json -Compress
""",
            )
        )
        print(json.dumps({"deployed": deployment}, ensure_ascii=False))
    finally:
        run_ps(
            session,
            f"Remove-Item -LiteralPath {powershell_literal(staging)} -Recurse -Force -ErrorAction SilentlyContinue",
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - never prints credentials
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2) from None
