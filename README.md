# Vulcan

Vulcan e uma plataforma SaaS de Inteligencia Operacional com IA. O produto transforma dados operacionais reais em decisoes melhores, ajudando empresas a descobrir gargalos, reduzir desperdicio de tempo e encontrar oportunidades de automacao.

Slogan:

`Vulcan - Transformando operacoes em inteligencia.`

## Structure

- `frontend/web`: Next.js web application.
- `backend/api`: local SaaS API for auth, tenants, users, hierarchy, metrics, insights, notifications, AI routing, Supabase status, and agent gateway.
- `backend`: ingestion, query, and job services.
- `ai/api`: hybrid GPT + Llama AI service.
- `agentes`: Linux and Windows agent MVPs, installers, shared contract, and macOS placeholder.
- `shared`: shared TypeScript packages and schemas.
- `database/supabase`: PostgreSQL/Supabase-compatible schema.
- `docker/compose.yml`: local PostgreSQL support.
- `docs`: enterprise documentation.

## Local Setup

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
./scripts/bootstrap.sh
corepack pnpm supabase:validate
corepack pnpm supabase:migrate
corepack pnpm seed:demo
corepack pnpm demo:validate
corepack pnpm dev
```

Default local URLs:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:3001`
- Supabase demo login: `admin@vulcan.local`
- Supabase demo password: value in `SUPABASE_DEMO_ADMIN_PASSWORD`
- Local test login: `teste`
- Local test password: `teste`
- Local fallback login: `admin`
- Local fallback password: `admin`

If `3000` is busy, the frontend automatically tries `3002`, `3003`, and `3004`. The local `teste/teste` login is enabled only outside production by `LOCAL_TEST_AUTH_ENABLED` and `NEXT_PUBLIC_LOCAL_TEST_AUTH`; Supabase Auth is the production path.

## Demo Comercial

Gere a demo completa:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
corepack pnpm seed:demo
corepack pnpm demo:validate
```

Usuarios locais da demo:

```text
teste / teste
diretor / diretor
coordenador / coordenador
gerente / gerente
supervisor / supervisor
lider / lider
operador1 / operador1
operador2 / operador2
operador3 / operador3
```

Hierarquia demonstrativa:

```text
teste / Root Demo
└── Diretor Operacional
    └── Coordenador de Operações
        └── Gerente Operacional
            └── Supervisor de Faturamento
                └── Líder Operacional
                    ├── Operador 1
                    ├── Operador 2
                    └── Operador 3
```

O seed cria dispositivos Windows, Linux e macOS, eventos dos ultimos 30 dias, metricas operacionais, insights, notificacoes e auditoria. Leia `docs/DEMO.md`, `docs/DASHBOARD.md`, `docs/METRICS.md`, `docs/HIERARCHY.md` e `docs/QA.md`.

## Hybrid AI Setup

Set these values in `.env`:

```env
AI_PROVIDER=hybrid
OPENAI_API_KEY=replace-me
OPENAI_MODEL=gpt-5.5
AI_COMPLEX_MODEL=gpt-5.5
AI_OPERATIONAL_MODEL=llama-4-maverick
LLAMA_PROVIDER=openai-compatible
LLAMA_BASE_URL=http://localhost:11434/v1
LLAMA_MODEL=llama-4-maverick
OPENAI_TIMEOUT_SECONDS=60
OPENAI_MAX_OUTPUT_TOKENS=2000
```

GPT is used for complex executive analysis and Vulcan Copilot responses. Llama is prepared for operational classification, recurring summaries, and lower-cost pre-analysis before escalation to GPT.

See `docs/AI.md`, `docs/SUPABASE.md`, and `docs/LOCAL_SETUP.md` for details.

## Supabase

Supabase is the official platform layer for Auth, PostgreSQL, RLS, Storage, and optional Realtime.

```bash
corepack pnpm supabase:validate
corepack pnpm supabase:migrate
corepack pnpm seed:demo
```

See `docs/SUPABASE.md` for required variables and production rules.

## Windows Agent

Build the robust Windows agent package:

```bash
corepack pnpm agent:windows:build
```

Generated package:

```text
agentes/installers/windows/VulcanAgent-Windows-x64.zip
```

See `docs/AGENT.md` and `agentes/windows/README.md` for installation, GPO usage, privacy boundaries, service recovery and offline sync behavior.

## Linux Agent

Package the Linux agent:

```bash
corepack pnpm agent:linux:package
```

Install the demo agent bound to the local `teste` user:

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan/agentes/installers/linux
bash ./instalar-vulcan-teste.sh --backend-url "http://localhost:3001" --install-deps
```

See `docs/AGENT.md`, `docs/LINUX_AGENT.md` and `agentes/linux/README.md` for privacy policy flags, logs, uninstall and collection-quality notes for GNOME/Wayland.

## Venda E Piloto Pago

O Vulcan deve ser demonstrado como uma central de inteligencia operacional, nao como um painel decorativo. O roteiro recomendado esta em `docs/SALES_DEMO.md`.

Documentos de produto e operacao:

- `docs/ONBOARDING.md`: como ativar uma empresa nova.
- `docs/LGPD.md` e `docs/PRIVACY.md`: limites de coleta e mensagem de confianca.
- `docs/WHATSAPP.md` e `docs/EMAIL.md`: notificacoes fora do painel.
- `docs/OBSERVABILITY.md`: health checks, logs, auditoria e producao.
- `docs/WINDOWS_AGENT.md`, `docs/LINUX_AGENT.md`, `docs/MACOS_AGENT.md`: instalacao e estado dos agentes.
