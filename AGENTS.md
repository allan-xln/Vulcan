# AGENTS

## Product

Vulcan is a global B2B SaaS platform for AI-powered operational intelligence.

Official positioning:

`Vulcan is an AI-Powered Operational Intelligence Platform that helps companies discover inefficiencies, identify bottlenecks and unlock automation opportunities through real operational data.`

## Non-Negotiable Principles

- Multi-tenant from day one.
- One logical business database.
- Tenant isolation is mandatory.
- `tenant_id` is mandatory on business data.
- RLS and auditability are mandatory.
- No surveillance positioning.
- No spyware behavior.
- No keylogger.
- No screenshots.
- No clipboard capture.
- No indiscriminate private-content capture.
- GPT is never the source of truth.
- AI explains structured operational facts, metrics, scores, and alerts.
- Every score must be traceable and explainable.
- Every metric must expose formula and origin.
- Prefer clarity, maintainability, security, and incremental delivery.
- No fake implementations disguised as real.

## Required Stack

- Frontend: Next.js, TypeScript, Tailwind, SWR, Recharts.
- Backend: Python, FastAPI, Pydantic, PostgreSQL.
- Database: one PostgreSQL/Supabase-compatible database with RLS.
- AI: GPT through OpenAI, integrated in `ai/api`.
- Agent: privacy-safe background collector with policy-controlled operational event capture.
- Infra: Docker Compose, pnpm workspaces, pytest, Vitest, Playwright, GitHub Actions.

## Repository Rules

- Keep product language aligned to Vulcan operational intelligence.
- Do not reintroduce ClickHouse, Redis, or database-per-tenant architecture without an explicit architecture decision.
- Do not commit local secrets, virtual environments, caches, generated build folders, or package manager output directories.
- Keep documentation in `docs` current when architecture changes.
