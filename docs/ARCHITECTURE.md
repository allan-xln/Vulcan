# Architecture

## Product Architecture

Vulcan is organized as a modular SaaS monorepo. The platform separates collection, ingestion, deterministic processing, read APIs, AI analysis, and user experience.

## Runtime Components

- Frontend: Next.js in `frontend/web`.
- Backend APIs: FastAPI services in `backend/ingestion-gateway` and `backend/query-api`.
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

## Architectural Decisions

- One database, not one database per customer.
- `tenant_id` is mandatory on business data.
- PostgreSQL RLS is the isolation baseline.
- Llama handles operational preprocessing; GPT explains complex structured facts and does not define source-of-truth data.
- ClickHouse and Redis were removed from the active local stack to align with the one-database requirement.
- Build artifacts, virtual environments, caches, and generated package metadata are not product source.

## Current Risks

- Linux and Windows agents are MVP-functional, but still need signed per-device enrollment tokens, auto-update and full enterprise hardening before production rollout.
- Linux collection quality depends on the desktop session. GNOME/Wayland can block active-window detail; Vulcan reports this as limited collection instead of bypassing OS privacy controls.
- Supabase Auth must replace local fallback users before production.
- Some production CRUD flows and provider credentials still need final hardening.
