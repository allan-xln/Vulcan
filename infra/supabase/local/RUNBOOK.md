# Local Database Runbook

## Purpose
Provide a local Postgres container with the minimum Supabase-compatible objects required by Phase 2:
- `auth.users`
- `auth.uid()`
- `anon`, `authenticated`, `service_role` roles

This is a local validation path for the Phase 2 schema. It is not a replacement for a full Supabase stack.

## Flow
1. Start `db` with Docker Compose.
2. The container auto-runs `local/init/*.sql`.
3. Apply Phase 2 migrations and seeds.
4. Run Phase 2 verification, including a basic RLS smoke check.

## Seeded local auth identity
- User id: `11111111-1111-1111-1111-111111111111`
- Email: `owner@local.test`

