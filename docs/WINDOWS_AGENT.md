# Windows Agent

## Build

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
corepack pnpm agent:windows:build
```

Generated package:

```text
agentes/installers/windows/VulcanAgent-Windows-x64.zip
```

## Install

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\install.ps1 `
  -TenantId "TENANT_UUID" `
  -BackendUrl "https://api.vulcan.lanfuture.dev" `
  -EnrollmentToken "TOKEN_DO_TENANT" `
  -LinkedUser "operador1" `
  -RoleLevel "Operador" `
  -Department "Operacoes"
```

## Operations

Expected scripts:

- `install.ps1`;
- `uninstall.ps1`;
- `status.ps1`;
- `repair.ps1`;
- `install-gpo.cmd`.

## Validation

- service installed;
- heartbeat received;
- device registered;
- queue depth stable;
- sync succeeds after offline period;
- logs do not expose secrets;
- uninstall removes service cleanly.

## Current Caveat

The package can be built locally, but production confidence requires a real Windows machine test, including service recovery, install/uninstall, GPO/RMM command and offline queue behavior.
