# Ingestion Gateway

Tenant-aware telemetry ingestion gateway for the initial raw intake boundary.

## Current scope
- validates the telemetry batch contract
- authenticates ingestion keys per tenant
- verifies workstation and agent scope inside the authenticated tenant
- applies idempotency by `tenant_id + source_event_id`
- persists raw intake rows into Postgres

## Local run
```bash
source .env
source .venv/bin/activate
uvicorn app.main:app --reload --host "${INGESTION_API_HOST:-0.0.0.0}" --port "${INGESTION_API_PORT:-8010}" --app-dir services/ingestion-gateway
```

