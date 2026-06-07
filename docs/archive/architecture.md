# Macro Architecture

## Goal
Deliver a multi-tenant operational intelligence platform where transactional truth stays in Supabase/PostgreSQL and high-volume telemetry analytics stay in ClickHouse.

## Core decisions
1. Supabase is the control plane for authentication, tenant membership, row-level security, audit metadata and primary product configuration.
2. ClickHouse stores append-only telemetry events and derived aggregates for performant analytics workloads.
3. Redis is reserved for short-lived queues, idempotency keys and cache entries. It is not a source of truth.
4. AI services consume structured facts and derived metrics only. They explain alerts and scores but never generate authoritative business data.
5. Agents emit observability signals and approved telemetry only. No spyware capabilities are allowed.

## Initial bounded contexts
- `frontend/web`: tenant-facing control plane for analytics, alerts, audit views and explainability.
- `ai/api`: explanation and scoring API over structured inputs.
- `backend/ingestion-gateway`: reserved for signed telemetry ingestion and validation.
- `agent/collector`: reserved Windows-first collector layout with osquery-based observability only.
- `shared/domain`: shared domain types and invariants.
- `infra`: local infrastructure definitions and telemetry collector configuration.

## Trust boundaries
- Tenant data access is enforced in the transactional layer with RLS and service-role isolation.
- Telemetry ingestion uses signed credentials per tenant and per agent class.
- Cross-tenant analytics queries must always include tenant keys and be validated server-side before execution.
- AI endpoints accept only scoped datasets already filtered by tenant and authorization context.
