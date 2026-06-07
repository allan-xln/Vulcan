# Supabase Layout

Supabase remains the transactional control plane and source of truth for tenant-scoped product data.

## Layout
- `migrations/`: ordered SQL migrations
- `seeds/`: local development seed data
- `local/`: local Postgres compatibility bootstrap
- `validation/`: read-only verification SQL
- `SCHEMA.md`: schema notes and migration order

## Transactional foundation
- multi-tenant control-plane schema
- membership, role and permission model
- org hierarchy with closure support
- employee, workstation and agent foundation
- feature flags, operational event policies and usage
- append-only audit logs
- initial RLS policies for tenant isolation

## Ingestion foundation
- tenant-scoped ingestion API keys
- append-only raw operational event intake boundary
- idempotency by source event id within tenant scope
- local seed key for development validation

## Normalization foundation
- normalization run tracking
- deterministic normalized operational event storage
- replay-safe raw-to-normalized conversion boundary

## Operational facts foundation
- session slices derived from normalized session boundaries
- idle windows derived from normalized idle events
- application usage facts derived from normalized foreground app changes

## Daily metrics foundation
- daily operational metric runs
- deterministic daily user-level metrics
- replay-safe daily rollup snapshots

## Local apply
```bash
./scripts/db-up.sh
./scripts/apply-phase2-sql.sh
./scripts/verify-phase2.sh
./scripts/apply-phase3-sql.sh
./scripts/verify-phase3.sh
./scripts/apply-phase4-sql.sh
./scripts/verify-phase4.sh
./scripts/apply-phase5-sql.sh
./scripts/verify-phase5.sh
./scripts/apply-phase6-sql.sh
./scripts/verify-phase6.sh
```
