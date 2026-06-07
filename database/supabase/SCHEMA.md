# Supabase Schema

## Migration order
0. `local/init/001_supabase_compat.sql`
0. `local/init/002_local_auth_seed.sql`
1. `migrations/20260412000100_transactional_foundation.sql`
2. `migrations/20260412000200_transactional_functions.sql`
3. `migrations/20260412000300_transactional_rls.sql`
4. `seeds/001_local_dev.sql`
5. `migrations/20260412000400_ingestion_foundation.sql`
6. `seeds/002_phase3_local_dev.sql`
7. `migrations/20260412000500_normalization_foundation.sql`
8. `migrations/20260412000600_operational_facts_foundation.sql`
9. `migrations/20260412000700_daily_metrics_foundation.sql`
10. `validation/001_phase2_checks.sql`
11. `validation/002_phase2_rls_smoke.sql`
12. `validation/003_phase3_ingestion_checks.sql`
13. `validation/004_phase4_normalization_checks.sql`
14. `validation/005_phase5_operational_facts_checks.sql`
15. `validation/006_phase6_daily_metrics_checks.sql`

## Operational notes
- This schema assumes Supabase-provided `auth.users` and `auth.uid()`.
- The local run path bootstraps a minimal compatibility layer for plain Postgres so the transactional foundation can be validated without the full Supabase stack.
- Tenant writes should generally happen through authenticated application paths or service-role workflows, not direct SQL from browsers.
- `org_closure` is rebuilt by triggers when nodes or edges change. That keeps the implementation simple and correct, while leaving room for a more incremental maintenance strategy later.
- `audit_logs` is append-only and intended for read access by tenant members only.

## Linkage strategy
- `user_profiles.user_id -> auth.users.id` is the application profile extension.
- `memberships.user_id -> auth.users.id` links a user to a tenant role.
- `employee_profiles.membership_id` is optional so employee records can exist before a user account is invited.
