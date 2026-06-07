# Vulcan Windows Agent

Agente Windows enterprise do Vulcan.

Componentes:

- `VulcanAgent.exe`: serviço/coletor nativo Windows x64.
- `VulcanAgentSetup.exe`: instalador/controlador para instalação elevada.
- `VulcanAgent` service: heartbeat, sync, recovery e watchdog básico.
- `Vulcan Session Collector`: tarefa agendada no logon do usuário.
- `Vulcan Tray`: placeholder para status local futuro.
- fila offline em JSONL.
- logs em `ProgramData`.

## Privacidade

O agente não coleta senhas, teclas digitadas, conteúdo de mensagens, screenshots, áudio, webcam, clipboard, cookies ou tokens.

Coletas sensíveis ficam desligadas por padrão:

- título da janela;
- domínio/URL do navegador;
- lista de processos.

## O Que Coleta

- aplicativo ativo;
- título da janela, somente com `-CollectWindowTitle`;
- tempo por aplicativo;
- tempo por janela quando permitido;
- trocas de contexto;
- tempo ativo;
- tempo ocioso via Win32 `GetLastInputInfo`;
- hostname;
- usuário Windows;
- domínio/workgroup via usuário;
- versão do Windows;
- status online/offline/sincronizando;
- heartbeat;
- fila offline;
- erros do agente;
- IP local;
- memória aproximada do agente;
- política de coleta em uso.

## Instalação Local

PowerShell como Administrador:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
cd C:\Caminho\Para\VulcanAgent-Windows-x64
.\install.ps1 `
  -TenantId "00000000-0000-0000-0000-000000000301" `
  -BackendUrl "http://localhost:3001" `
  -EnrollmentToken "vulcan-local-enrollment-token" `
  -LinkedUser "teste" `
  -MembershipId "00000000-0000-0000-0000-000000300005" `
  -RoleLevel "user" `
  -Department "Operacoes"
```

Com título da janela habilitado por política:

```powershell
.\install.ps1 `
  -TenantId "00000000-0000-0000-0000-000000000301" `
  -BackendUrl "http://localhost:3001" `
  -EnrollmentToken "vulcan-local-enrollment-token" `
  -LinkedUser "teste" `
  -MembershipId "00000000-0000-0000-0000-000000300005" `
  -RoleLevel "user" `
  -Department "Operacoes" `
  -CollectWindowTitle
```

## Instalação Em Massa

Distribua `VulcanAgent-Windows-x64.zip` por GPO, Intune, SCCM ou RMM:

```cmd
install-gpo.cmd -TenantId "TENANT_UUID" -BackendUrl "https://api.suaempresa.com" -EnrollmentToken "TOKEN_DO_TENANT" -RoleLevel "Operador" -Department "Operacoes"
```

## Operação

Status:

```powershell
.\status.ps1
Get-Service VulcanAgent
```

Logs:

```powershell
Get-Content "C:\ProgramData\Vulcan\Agent\logs\agent.log" -Wait
```

Reiniciar:

```powershell
Restart-Service VulcanAgent
```

Testar conexão:

```powershell
& "C:\Program Files\Vulcan\Agent\VulcanAgentCtl.exe" heartbeat
& "C:\Program Files\Vulcan\Agent\VulcanAgentCtl.exe" sync
```

Desinstalar:

```powershell
.\uninstall.ps1
```

Remover tudo:

```powershell
.\uninstall.ps1 -PurgeData
Remove-Item -Recurse -Force "C:\Program Files\Vulcan\Agent" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "C:\ProgramData\Vulcan\Agent" -ErrorAction SilentlyContinue
```

## Arquivos

- Binário: `C:\Program Files\Vulcan\Agent\VulcanAgent.exe`
- Controle: `C:\Program Files\Vulcan\Agent\VulcanAgentCtl.exe`
- Config: `C:\ProgramData\Vulcan\Agent\config\agent.json`
- Fila offline: `C:\ProgramData\Vulcan\Agent\queue\events.jsonl`
- Logs: `C:\ProgramData\Vulcan\Agent\logs\agent.log`

## MSI

O MVP entrega EXE nativo e scripts silenciosos. MSI/MSIX deve ser empacotado em etapa posterior com WiX Toolset ou MSIX Packaging Tool.
