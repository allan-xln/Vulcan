# Agentes

Esta página resume a operação dos agentes Vulcan. A documentação detalhada permanece em `docs/AGENT.md`.

## Plataformas

- Linux: agente Python com instalador amigável e serviço `systemd --user`.
- Windows: pacote enterprise com serviço, coletor de sessão, instalador e scripts para GPO/Intune/RMM.
- macOS: skeleton funcional com Python 3, LaunchAgent, heartbeat, fila offline e sync. Falta pacote `.pkg` assinado/notarizado para produção.

## Linux Local

Instalar o agente no notebook atual vinculado ao usuário `teste`:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/agentes/installers/linux
bash ./instalar-vulcan-teste.sh \
  --backend-url "http://localhost:3001" \
  --install-deps \
  --collect-window-title \
  --collect-process-list
```

Status:

```bash
./status.sh
systemctl --user status vulcan-agent.service --no-pager
```

Logs:

```bash
journalctl --user -u vulcan-agent.service -f
tail -f ~/.local/state/vulcan-agent/logs/agent.log
```

Reiniciar:

```bash
systemctl --user restart vulcan-agent.service
```

Desinstalar:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/agentes/installers/linux
bash ./uninstall.sh
```

Remover tudo:

```bash
bash ./uninstall.sh --purge
```

## Windows

Pacote esperado:

```text
agentes/installers/windows/VulcanAgent-Windows-x64.zip
```

## macOS

Instalar skeleton local:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/agentes/macos
bash ./install.sh \
  --backend-url "http://localhost:3001" \
  --tenant-id "00000000-0000-0000-0000-000000000301" \
  --enrollment-token "vulcan-local-enrollment-token"
```

Status:

```bash
./status.sh
tail -f "$HOME/Library/Logs/VulcanAgent/agent.log"
```

Sem `membership-id`, o macOS aparece no painel como dispositivo aguardando adoção.

Instalação local em PowerShell Admin:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\install.ps1 `
  -TenantId "00000000-0000-0000-0000-000000000301" `
  -BackendUrl "http://localhost:3001" `
  -EnrollmentToken "vulcan-local-enrollment-token" `
  -LinkedUser "teste" `
  -RoleLevel "user" `
  -Department "Operacoes"
```

## O Que O Agente Envia

- aplicativo ativo;
- título da janela quando permitido por política;
- duração;
- tempo ativo;
- tempo ocioso;
- trocas de contexto;
- heartbeat;
- qualidade da coleta;
- status de sincronização;
- fila offline;
- hostname;
- sistema operacional;
- versão do agente;
- IP local;
- erros do agente.

## Confiabilidade De Sincronização

O backend trata `eventId` do agente como `source_event_id` idempotente por tenant. Se o agente reenviar o mesmo evento por timeout ou queda de rede, o banco mantém apenas uma linha em `activity_events`.

Para reduzir timeout em Supabase remoto:

- Linux sincroniza lotes de 100 eventos por padrão.
- Windows sincroniza lotes de 100 eventos por padrão.
- Timeout HTTP dos agentes foi elevado para 30 segundos.
- O backend grava auditoria por lote em vez de uma linha de auditoria por evento.

O agente ainda mantém fila offline local. Se a API ficar fora do ar, os eventos permanecem no arquivo local e são reenviados quando o backend voltar.

## O Que O Agente Não Envia

- senhas;
- teclas digitadas;
- conteúdo de conversas;
- prints contínuos;
- webcam;
- áudio;
- clipboard irrestrito;
- cookies;
- tokens.
