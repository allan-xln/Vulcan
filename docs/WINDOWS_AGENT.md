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
# Agente Windows

O agente Windows deve rodar como serviço corporativo auditável:

- serviço `VulcanAgent`;
- descrição `Vulcan Operational Intelligence Agent`;
- início com o Windows;
- recovery automático;
- heartbeat;
- fila offline;
- retry/sync;
- logs locais;
- desinstalação autorizada.

Não implemente ocultação maliciosa, bypass de UAC, alteração de antivírus, keylogger, áudio, webcam ou prints contínuos.

Build:

```bash
cd /home/allan/Dev/Vulcan
corepack pnpm agent:windows:build
```

Instalação piloto autorizada:

```powershell
.\install.ps1 `
  -TenantId "00000000-0000-0000-0000-000000000301" `
  -BackendUrl "http://192.168.200.4:3001" `
  -EnrollmentToken "TOKEN_RUNTIME" `
  -LinkedUser "$env:COMPUTERNAME\$env:USERNAME" `
  -CorporateMonitoring `
  -NoElevationPrompt
```
