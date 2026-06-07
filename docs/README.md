# Vulcan Documentation

Vulcan is an AI-powered operational intelligence platform that transforms operational data into explainable decisions.

Official slogan:

`Vulcan - Transformando operacoes em inteligencia.`

Global positioning:

`Vulcan is an AI-Powered Operational Intelligence Platform that helps companies discover inefficiencies, identify bottlenecks and unlock automation opportunities through real operational data.`

## Official Product Scope

Vulcan is focused on:

- operational intelligence
- bottleneck discovery
- process efficiency
- productivity insights
- automation opportunities
- rework reduction
- data-backed recommendations

Vulcan is not a surveillance, espionage, or monitoring product. The agent must never collect passwords, keystrokes, clipboard contents, screenshots, or private content outside approved operational event signals.

## Repository Map

- `frontend/web`: Next.js application.
- `backend/api`: local SaaS API for auth, tenants, users, devices, hierarchy, metrics, insights, notifications, AI routes, and Supabase status.
- `backend/ingestion-gateway`: tenant-scoped operational event ingestion API.
- `backend/query-api`: tenant-scoped read API.
- `backend/jobs`: deterministic normalization, fact derivation, and metric rollup jobs.
- `ai/api`: Vulcan AI API backed by hybrid GPT + Llama routing.
- `agentes`: Linux and Windows privacy-safe agents, installers and shared API contract. macOS remains a future placeholder.
- `shared/domain`: shared frontend domain constants.
- `shared/operational-event-schema`: shared operational event schema.
- `database/supabase`: PostgreSQL/Supabase-compatible schema, migrations, seeds, and validation SQL.
- `docker/compose.yml`: local Postgres and optional local AI runtime support.
- `docs`: enterprise documentation.
- `tests/fixtures`: shared fixtures.

## Required Reading

- `ARCHITECTURE.md`
- `DATABASE.md`
- `MULTITENANCY.md`
- `SECURITY.md`
- `AI.md`
- `AGENT.md`
- `BACKEND.md`
- `FRONTEND.md`
- `SUPABASE.md`
- `LOCAL_SETUP.md`
- `NOTIFICATIONS.md`
- `API.md`
- `DEPLOY.md`
- `ROADMAP.md`
