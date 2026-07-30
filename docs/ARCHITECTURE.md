# Architecture

## Product Architecture

Vulcan is organized as a modular SaaS monorepo. The platform separates collection, ingestion, deterministic processing, read APIs, AI analysis, and user experience.

## Runtime Components

- Frontend: Next.js in `frontend/web`.
- Backend principal: FastAPI em `backend/api`, incluindo autenticação, Workforce,
  Infrastructure, Timeline, Agents, Wallboards e realtime.
- Serviços especializados preservados em `backend/ingestion-gateway` e
  `backend/query-api`, ativados conforme o perfil de execução.
- Platform API: router modular em `backend/api/app/platform_routes.py`, composto à API existente.
- Discovery: worker Python independente em `backend/discovery`, somente leitura e desativado por padrão.
- Infrastructure sync: worker de reconciliação somente leitura para UniFi e Proxmox,
  sem expor credenciais ao frontend.
- Jobs: Python workers in `backend/jobs`.
- AI: FastAPI service in `ai/api`, using hybrid GPT + Llama routing.
- Database: one Supabase PostgreSQL database in `database/supabase`.
- Agent: collectors and installers in `agentes` for Linux and Windows, with macOS reserved for a future version.

## Data Flow

1. The Vulcan agent collects approved operational event signals under an explicit privacy policy.
2. The agent sends enrollment, heartbeat, activity events, quality signals and sync status to the API.
3. The backend authenticates the enrollment token and persists data with `tenant_id`.
4. Raw operational events are stored in PostgreSQL and converted into operational metrics.
5. Jobs derive session slices, idle windows, app usage facts, context switching and daily metrics.
6. Query APIs expose tenant-scoped and hierarchy-aware reads.
7. Llama classifies and pre-analyzes operational patterns.
8. GPT analyzes complex cases and returns executive recommendations.

Eventos atuais de `activity_events` são espelhados de forma idempotente para
`unified_events`. A timeline consulta esse modelo canônico por cursor e o frontend recebe
novos eventos por SSE autenticado e isolado por tenant/escopo.

Infraestrutura usa tabelas relacionais para sites, redes, ativos, interfaces,
relacionamentos, políticas/execuções/achados de descoberta, incidentes, retenção e módulos
por tenant. O inventário nunca armazena o valor de credenciais: integrações guardam apenas
uma referência de segredo.

Os Wallboards Workforce e Infrastructure consomem snapshots reais do mesmo banco,
respeitam site/tenant, recebem sinais de atualização por SSE e não possuem endpoints
privilegiados próprios. Perfis, playlists e ordem dos painéis são persistidos com RLS e
auditoria.

## Architectural Decisions

- One database, not one database per customer.
- `tenant_id` is mandatory on business data.
- PostgreSQL RLS is the isolation baseline.
- Llama handles operational preprocessing; GPT explains complex structured facts and does not define source-of-truth data.
- ClickHouse and Redis were removed from the active local stack to align with the one-database requirement.
- Redis do stack atual pertence à Evolution; não é cache do Vulcan.
- NATS, ClickHouse, VictoriaMetrics, MinIO e OpenTelemetry Collector dependem de ADR,
  benchmark e necessidade medida antes de entrar no runtime.
- Workforce permanece o módulo inicial. Infrastructure e Timeline compartilham o mesmo
  backend, autenticação, tenant, RLS, permissões e auditoria.
- Build artifacts, virtual environments, caches, and generated package metadata are not product source.

## Current Risks

- O MSI e o serviço Windows ainda precisam de homologação em Windows real antes de
  implantação em massa.
- A coleta Linux depende da sessão gráfica. GNOME/Wayland pode limitar a janela ativa; o
  agente reporta a limitação e não contorna controles de privacidade do sistema.
- A produção usa autenticação real pelo PostgreSQL; o modo local/demo é bloqueado em
  ambiente `production`.
- UniFi e Proxmox possuem adapters somente leitura. SNMP, FortiGate, syslog, traps e flows
  continuam explicitamente não implementados.
- HTTP privado é permitido para a rede interna atual com opt-in explícito no agente; TLS
  interno confiável permanece como hardening prioritário.
