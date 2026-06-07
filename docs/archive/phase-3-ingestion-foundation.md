# Phase 3 Ingestion Foundation

## Goal
Implement the initial telemetry ingestion boundary with strong validation, tenant-aware authentication, idempotency and raw persistence.

## Decisions
- The accepted contract is versioned as `2026-06-operational-events.v1`.
- Ingestion is authenticated by `X-Ingestion-Key-Id` and `X-Ingestion-Key`, resolved against tenant-scoped hashed keys in Postgres.
- The first persistence boundary is `public.raw_operational_event_intake`, not ClickHouse.
- Idempotency is enforced by unique `(tenant_id, source_event_id)`.
- Scope validation ensures the workstation and optional agent installation belong to the authenticated tenant before acceptance.

## API surface
- `POST /v1/operational-events/batches`
- `GET /health`

## Headers
- `X-Ingestion-Key-Id`
- `X-Ingestion-Key`

## Persistence boundary
- `ingestion_api_keys`: tenant-scoped ingestion credentials
- `raw_operational_event_intake`: append-only accepted raw events plus duplicate detection

## Out of scope in this phase
- enrichment
- analytics feature generation
- anomaly detection
- dashboard rollups
- ClickHouse persistence

