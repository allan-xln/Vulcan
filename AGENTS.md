# AGENTS

## Product
SaaS B2B de inteligência operacional com telemetria corporativa, analytics hierárquico e camada de IA explicável.

## Non-negotiable principles
- Multi-tenant from day one.
- Tenant isolation is mandatory.
- RLS and auditability are mandatory.
- No spyware behavior.
- No keylogger, no continuous screenshots, no indiscriminate content capture.
- LLM is never the source of truth.
- AI only explains structured facts, features, scores and alerts.
- Every score must be traceable and explainable.
- Every metric must expose formula and origin.
- Prefer clarity, maintainability, security and incremental delivery.
- No fake implementations disguised as real.
- No unnecessary dependencies.
- Do not change the required stack without strong technical justification.

## Required stack
- Frontend: Next.js, TypeScript, Tailwind, shadcn/ui, React Query or SWR, Recharts or ECharts
- Transactional backend: Supabase, PostgreSQL, Auth, RLS, Storage, Realtime
- Analytics: ClickHouse, Redis, OpenTelemetry, Fluent Bit or Grafana Alloy
- AI services: Python, FastAPI, Pydantic, SQLAlchemy when applicable, Ollama or vLLM
- Local agent: Windows-first MVP with osquery-based observability and a lightweight collector
- Infra: Docker, Docker Compose, pnpm workspaces, monorepo, pytest, Vitest, Playwright, GitHub Actions

## Execution rules
- Work in phases.
- In each phase, generate real files, real code, real commands and validation steps.
- Keep the repository consistent after every change.
- Do not jump ahead if the foundation is missing.
- Prefer the smallest correct change that leaves the repo in a professional state.

## Expected response format
For every relevant task:
1. Goal
2. Decision
3. File structure
4. Code
5. Commands
6. Validation
7. Next step