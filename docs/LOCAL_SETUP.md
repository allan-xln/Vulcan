# Local Setup

## Install Dependencies

```bash
./scripts/bootstrap.sh
corepack pnpm supabase:validate
corepack pnpm supabase:migrate
corepack pnpm seed:demo
```

If `pnpm` is not globally available, the scripts use `corepack pnpm` when available.

## Run Everything

```bash
corepack pnpm dev
```

This starts:

- frontend: `http://localhost:3002` when port `3000` is busy, otherwise `http://localhost:3000`
- backend API: `http://localhost:3001`

If `3000` is already occupied, `scripts/dev.sh` automatically tries `3002`, `3003`, and `3004`. You can force a port with:

```bash
FRONTEND_PORT=3002 corepack pnpm dev
```

Para subir Vulcan + Evolution/Baileys + worker de WhatsApp com os scripts operacionais:

```bash
./scripts/docker-up.sh
```

Esse comando sobe tudo em Docker: Postgres, Evolution, Redis, backend, worker e frontend. Documentacao completa: `docs/DOCKER.md`.
No stack completo, a Evolution fica interna no Docker e nao publica porta para usuario final.

Para conectar o celular no WhatsApp mestre:

```bash
./scripts/docker-whatsapp-qr.sh 55DDDNUMERO
```

Fluxo sem Docker para desenvolvimento direto:

```bash
./scripts/start-all.sh
./scripts/status-all.sh
./scripts/logs-all.sh
```

Parar tudo:

```bash
./scripts/stop-all.sh
```

## Local Login

Fastest development account:

```text
username: teste
password: teste
```

This account is intentionally local-only and disabled in production with:

```env
LOCAL_TEST_AUTH_ENABLED=false
NEXT_PUBLIC_LOCAL_TEST_AUTH=false
```

Supabase demo user after `corepack pnpm seed:demo`:

```text
email: admin@vulcan.local
password: value of SUPABASE_DEMO_ADMIN_PASSWORD, default VulcanAdmin123! for local demo
```

Admin development fallback:

```text
username: admin
password: admin
```

Commercial demo profiles after `corepack pnpm seed:demo`:

```text
diretor / diretor
coordenador / coordenador
gerente / gerente
supervisor / supervisor
lider / lider
operador1 / operador1
operador2 / operador2
operador3 / operador3
```

Equivalent local e-mails:

```text
diretor@vulcan.local / diretor
coordenador@vulcan.local / coordenador
gerente@vulcan.local / gerente
supervisor@vulcan.local / supervisor
lider@vulcan.local / lider
operador1@vulcan.local / operador1
operador2@vulcan.local / operador2
operador3@vulcan.local / operador3
teste@vulcan.local / teste
```

Restart `corepack pnpm dev` after changing `.env`; uvicorn reloads code, but the parent shell environment is loaded when the process starts.

## OpenAI

The real `OPENAI_API_KEY` belongs only in `.env`. Never commit it.

Required:

```env
OPENAI_API_KEY=replace-me
AI_PROVIDER=hybrid
AI_COMPLEX_MODEL=gpt-5.5
AI_OPERATIONAL_MODEL=llama-4-maverick
```

## Llama

The Llama operational layer is configured through OpenAI-compatible environment variables:

```env
LLAMA_PROVIDER=openai-compatible
LLAMA_BASE_URL=http://localhost:11434/v1
LLAMA_MODEL=llama-4-maverick
LLAMA_API_KEY=
```

If no Llama endpoint is running, Vulcan keeps the operational layer mocked and documented.

## Supabase

Validate Supabase credentials and REST/database reachability:

```bash
corepack pnpm supabase:validate
```

Apply Supabase migrations:

```bash
corepack pnpm supabase:migrate
```

Generate deterministic demo data:

```bash
corepack pnpm seed:demo
```

O seed cria o tenant `Vulcan Demo`, usuarios de teste por nivel hierarquico, departamentos, cargos, fechamento da hierarquia, dispositivos Windows/Linux/macOS, eventos dos ultimos 30 dias, metricas operacionais, insights de IA, notificacoes, preferencias, configuracoes de provedores e logs de auditoria.

Documentacao da demo:

```text
docs/DEMO.md
docs/DASHBOARD.md
docs/METRICS.md
docs/HIERARCHY.md
docs/QA.md
```

Validate the commercial demo scopes through the API:

```bash
corepack pnpm demo:validate
```

This command logs in as every demo profile and verifies hierarchy visibility, devices, operational intelligence and notifications. It fails if a profile sees names or device owners outside its expected reporting tree.

## WhatsApp, E-mail E Notificações

O Vulcan já expõe endpoints para status e teste de WhatsApp/e-mail. Sem credenciais reais, eles retornam estado controlado de configuração pendente.

```bash
curl -H "Authorization: Bearer dev-vulcan-admin-token" http://localhost:3001/integrations/whatsapp/status
curl -H "Authorization: Bearer dev-vulcan-admin-token" http://localhost:3001/integrations/email/status
```

Canal WhatsApp raiz com Evolution/Baileys:

```env
ROOT_WHATSAPP_ENABLED=true
ROOT_WHATSAPP_PROVIDER=evolution
ROOT_WHATSAPP_NUMBER=
ROOT_WHATSAPP_NAME=Notificações Vulcan
ROOT_WHATSAPP_MOCK_MODE=false
EVOLUTION_ENABLED=true
EVOLUTION_BASE_URL=http://127.0.0.1:8080
EVOLUTION_API_KEY=
EVOLUTION_INSTANCE_NAME=vulcan-root
EVOLUTION_WEBHOOK_URL=http://127.0.0.1:3001/integrations/whatsapp/evolution/webhook
EVOLUTION_WEBHOOK_TOKEN=
WHATSAPP_PROVIDER=evolution
WHATSAPP_REQUIRE_OPT_IN=true
WHATSAPP_ENABLE_UNOFFICIAL_PROVIDER=true
WHATSAPP_GRAPH_API_VERSION=v25.0
```

Com `ROOT_WHATSAPP_MOCK_MODE=true`, o Vulcan cria fila, historico e auditoria, mas nao envia mensagem real.

Evolution/Baileys nao e API oficial da Meta. Para QR Code:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/infra/evolution
./scripts/start.sh
./scripts/status.sh
```

No runtime Docker completo, use `./scripts/docker-whatsapp-qr.sh 55DDDNUMERO`. Pela UI, entre como owner (`admin/admin` no local), abra `Configuracoes -> WhatsApp` e clique em `Ver QR`. Usuarios de tenant nao veem URL, API key, QR, fila ou logs tecnicos.

Autostart:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
./scripts/install-evolution-autostart.sh
```

Detalhes: `docs/WHATSAPP_EVOLUTION.md` e `docs/WHATSAPP_ROOT_CHANNEL.md`.

SMTP:

```env
EMAIL_PROVIDER=smtp
EMAIL_DELIVERY_MODE=mock
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
EMAIL_FROM=
```

Use `EMAIL_DELIVERY_MODE=live` apenas quando quiser validar conexão SMTP real.

## Windows Agent

Build the Windows x64 agent package:

```bash
corepack pnpm agent:windows:build
```

Generated files:

```text
agentes/installers/windows/VulcanAgent.exe
agentes/installers/windows/VulcanAgentSetup.exe
agentes/installers/windows/VulcanAgent-Windows-x64.zip
```

Install on a Windows machine after extracting the zip:

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

For GPO/Intune/RMM:

```cmd
install-gpo.cmd -TenantId "TENANT_UUID" -BackendUrl "https://api.suaempresa.com" -EnrollmentToken "TOKEN_DO_TENANT" -RoleLevel "Operador" -Department "Operacoes"
```

## Linux Agent

Package the Linux agent:

```bash
corepack pnpm agent:linux:package
```

Install on this Linux desktop with the local backend using the friendly installer package:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/agentes/installers/linux
bash ./instalar-vulcan-teste.sh --backend-url "http://localhost:3001" --install-deps
```

For the demo tenant, `--linked-user "teste"` automatically binds the agent to demo membership:

```text
00000000-0000-0000-0000-000000300005
```

Useful commands:

```bash
./status.sh
journalctl --user -u vulcan-agent.service -f
systemctl --user restart vulcan-agent.service
./uninstall.sh
./uninstall.sh --purge
```

For GNOME/Wayland desktops, the OS may block detailed active-window data. In that case the agent still sends heartbeat, uptime, queue, idle/session signals where available, and collection quality appears as limited in the dashboard. For a stronger opt-in setup:

```bash
bash ./instalar-vulcan-teste.sh \
  --backend-url "http://localhost:3001" \
  --install-deps \
  --collect-window-title \
  --collect-process-list
```
