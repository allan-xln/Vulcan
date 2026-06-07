# Vulcan Agent

O Vulcan Agent e o componente local responsavel por transformar atividade operacional em eventos estruturados para a plataforma Vulcan.

Ele foi desenhado como software corporativo legitimo de inteligencia operacional. Nao e spyware, nao tem modulo de captura de teclado, nao captura senhas, nao tira screenshots, nao grava audio, nao usa webcam e nao le clipboard livremente.

## Status atual

Windows esta preparado como MVP funcional:

- fonte: `agentes/windows/agent`
- build: `corepack pnpm agent:windows:build`
- binario silencioso para servico/coletor: `agentes/installers/windows/VulcanAgent.exe`
- instalador/controlador EXE: `agentes/installers/windows/VulcanAgentSetup.exe`
- pacote para distribuicao: `agentes/installers/windows/VulcanAgent-Windows-x64.zip`

Linux esta preparado como MVP funcional com Python 3 e `systemd --user`:

- fonte: `agentes/linux/vulcan_agent.py`
- pacote: `corepack pnpm agent:linux:package`
- instalador: `agentes/linux/install.sh`
- pacote para distribuicao: `agentes/installers/linux/VulcanAgent-Linux.zip`

macOS possui estrutura e contrato compartilhado preparados em `agentes/macos` e `agentes/shared`.

## Arquitetura Windows

O agente Windows separa responsabilidades:

- `VulcanAgent` Windows Service: heartbeat, retry, sync, fila offline, recovery automatico.
- `Vulcan Session Collector`: tarefa por usuario logado, coleta app/janela ativa.
- `Vulcan Tray`: placeholder para UI futura do usuario, consentimento/status e diagnostico.

Essa separacao e importante porque servicos Windows rodam na session 0 e nao devem depender dela para capturar janelas da sessao do usuario.

## Politica De Coleta

O agente possui uma camada de política. No Linux ela fica em:

```text
~/.config/vulcan/agent/agent-policy.json
```

No Windows a política fica dentro de:

```text
C:\ProgramData\Vulcan\Agent\config\agent.json
```

Flags principais:

- `collectAppName`
- `collectWindowTitle`
- `collectIdleTime`
- `collectSessionEvents`
- `collectBrowserDomain`
- `collectBrowserUrl`
- `collectProcessList`
- `collectSystemMetrics`
- `redactSensitiveTerms`
- `syncIntervalSeconds`
- `heartbeatIntervalSeconds`
- `offlineQueueEnabled`
- `maxOfflineQueueSize`
- `allowUserPause`
- `showTrayStatus`
- `privacyMode`

Por padrão, `collectWindowTitle`, `collectBrowserDomain`, `collectBrowserUrl` e `collectProcessList` ficam desligados quando houver risco de excesso de coleta.

## Dados coletados

Permitido:

- aplicativo ativo;
- titulo da janela ativa somente se a politica permitir;
- timestamps de inicio/fim;
- duracao em segundos;
- troca de contexto;
- tempo ativo;
- tempo ocioso;
- bloqueio/desbloqueio de sessao quando o sistema permitir;
- retorno de suspensao;
- hostname;
- usuario do sistema operacional;
- versao do sistema operacional;
- uptime;
- IP local;
- versao do agente;
- status online/offline/sincronizando;
- heartbeat;
- qualidade da coleta;
- erros de coleta;
- fila offline;
- categoria de aplicativo;
- saude do agente;
- tenant, membership, nivel/cargo e departamento informados na instalacao;
- dominio/URL do navegador somente quando a politica permitir, com redaction e sem querystring por padrão;
- lista limitada de processos somente quando a politica permitir, sem argumentos.

Bloqueado por desenho:

- senhas;
- teclas digitadas;
- screenshots;
- audio;
- webcam;
- conteudo privado de mensagens;
- clipboard irrestrito;
- inspecao de arquivos pessoais.

Titulos potencialmente sensiveis sao redigidos automaticamente quando contem termos como senha, token, banco, WhatsApp, login ou conteudo confidencial.

## Eventos Do Agente

O backend aceita eventos ricos:

- `app_focus_started`
- `app_focus_ended`
- `context_switch`
- `idle_started`
- `idle_ended`
- `session_locked`
- `session_unlocked`
- `user_logged_in`
- `user_logged_out`
- `machine_sleep`
- `machine_resume`
- `heartbeat`
- `sync_status`
- `collection_quality`
- `agent_error`
- `agent_health`

Métricas derivadas atuais:

- `app_usage_seconds`
- `active_seconds`
- `idle_seconds`
- `context_switch_count`
- `agent_error_count`
- `collection_quality_score`
- `agent_memory_mb`

O backend também consolida esses sinais em `/operational-intelligence`, exibindo no frontend:

- tempo por sistema;
- tempo ocioso;
- trocas de contexto por hora;
- foco contínuo;
- tempo fragmentado;
- dispersão operacional estimada;
- ranking de apps;
- qualidade da coleta;
- recomendações de IA operacional.

A heurística de processos no Linux ignora processos técnicos como `ps`, `runc`, `systemd`, `node`, shells internos e processos do próprio Vulcan. Em Wayland, se não houver acesso confiável à janela ativa, a qualidade é marcada como limitada em vez de inventar precisão.

## Endpoints

O backend principal expõe:

- `GET /agent/status`
- `POST /agent/enroll`
- `POST /agent/heartbeat`
- `POST /agent/events`
- `POST /agent/sync`
- `POST /agent/logs`

Todos os POSTs usam `enrollmentToken`, configurado no backend por:

```env
AGENT_ENROLLMENT_TOKEN=vulcan-local-enrollment-token
```

Em producao, esse token deve ser rotacionavel e preferencialmente emitido por tenant, com expiracao e auditoria de criacao.

## Instalacao Windows local

No Windows, extraia `VulcanAgent-Windows-x64.zip` e rode como administrador:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\install.ps1 `
  -TenantId "00000000-0000-0000-0000-000000000301" `
  -BackendUrl "http://localhost:3001" `
  -EnrollmentToken "vulcan-local-enrollment-token" `
  -LinkedUser "Operador 1" `
  -RoleLevel "Operador" `
  -Department "Operacoes"
```

Para instalar permitindo titulo de janela filtrado:

```powershell
.\install.ps1 -TenantId "TENANT_UUID" -BackendUrl "https://api.vulcan.local" -EnrollmentToken "TOKEN" -CollectWindowTitle
```

## Instalacao em massa

Para GPO, Intune, SCCM ou RMM:

```cmd
install-gpo.cmd -TenantId "TENANT_UUID" -BackendUrl "https://api.suaempresa.com" -EnrollmentToken "TOKEN_DO_TENANT" -RoleLevel "Operador" -Department "Operacoes"
```

O instalador cria:

- servico `VulcanAgent` com auto-start;
- recovery com restart automatico;
- tarefa `Vulcan Session Collector` no logon;
- tarefa `Vulcan Tray` como placeholder futuro;
- binario de controle `VulcanAgentCtl.exe` em `C:\Program Files\Vulcan\Agent`;
- config em `C:\ProgramData\Vulcan\Agent\config\agent.json`;
- fila offline em `C:\ProgramData\Vulcan\Agent\queue\events.jsonl`;
- logs em `C:\ProgramData\Vulcan\Agent\logs\agent.log`.

## Operacao

```powershell
.\status.ps1
.\repair.ps1
.\uninstall.ps1
.\uninstall.ps1 -PurgeData
```

## Instalacao Linux local

Com o backend rodando em `http://localhost:3001`:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/agentes/installers/linux
bash ./instalar-vulcan-teste.sh --backend-url "http://localhost:3001" --install-deps
```

Com coletas sensíveis explicitamente habilitadas:

```bash
bash ./instalar-vulcan-teste.sh \
  --backend-url "http://localhost:3001" \
  --install-deps \
  --collect-window-title \
  --collect-process-list
```

Operacao Linux:

```bash
./status.sh
journalctl --user -u vulcan-agent.service -f
systemctl --user restart vulcan-agent.service
./uninstall.sh
./uninstall.sh --purge
```

## Banco

O agente alimenta:

- `devices`
- `activity_events`
- `operational_metrics`
- `audit_logs`

Todo payload inclui `tenant_id` e e validado pelo backend antes de persistir. A camada de repositorio usa o tenant informado e grava auditoria para enrollment, heartbeat e eventos armazenados.

## Proximas melhorias

- MSI com WiX Toolset/MSIX para distribuicao Microsoft completa.
- Tray real com status, pausa controlada por politica e diagnostico.
- tokens de enrollment por tenant com expiracao.
- assinatura de payloads com chave por instalacao.
- auto-update com canal, rollback e kill switch.
- extensão/controlador opt-in para URL de navegador por domínio com consentimento formal.
