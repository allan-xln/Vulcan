# Multitenancy

## Model

Vulcan uses a shared-database, shared-schema SaaS model. Tenant isolation is enforced by:

- mandatory `tenant_id` on business tables
- foreign keys to `tenants`
- composite uniqueness scoped by tenant
- row-level security policies
- tenant membership checks
- service-level authorization before database access
- audit logs carrying tenant context

## Isolation Rules

- Business reads must be scoped by tenant.
- Business writes must provide tenant context.
- Jobs must run for one tenant at a time.
- Ingestion keys are tenant scoped.
- Operational event sources are validated against the authenticated tenant.
- AI requests receive only structured facts for the active tenant.
- Supabase Auth users must map to one or more `memberships`.
- User visibility is resolved by `membership_closure`: self plus descendants, unless the role has tenant or global scope.

## Advantages

- Operationally simpler than database-per-tenant.
- Easier global schema migration.
- Lower infrastructure cost.
- Better fit for shared SaaS analytics.
- Enables cross-tenant benchmark products later using anonymized, aggregated datasets.

## Risks And Controls

- Risk: missing tenant filter in application SQL.
  Control: RLS plus repository-level tenant filters.

- Risk: unassigned agent rows leak before a device is linked.
  Control: RLS requires tenant membership before allowing null `owner_membership_id` or null `membership_id` rows to be read.

- Risk: service-role bypass of RLS.
  Control: service-role usage must be limited to internal workflows and tested with tenant-specific inputs.

- Risk: AI prompt contains data from multiple tenants.
  Control: AI API accepts tenant-scoped structured facts only.

- Risk: global jobs leak data.
  Control: job requests require `tenant_id`; fan-out must happen outside the job.

- Risk: manager sees users outside their reporting tree.
  Control: RLS policies call hierarchy functions that check `membership_closure`.

## Application Authorization

The backend repository mirrors RLS rules before every direct Postgres query:

- root users: all tenants.
- tenant/global scope: active tenant only.
- hierarchy scope: active membership plus descendants from `membership_closure`.
- self scope: active membership only.

Direct database access uses backend secrets and can bypass RLS at the PostgreSQL role level, so service-side filters and tests are mandatory. Browser and Supabase Auth access must rely on public keys plus RLS.

## Commercial Smoke Tests

The current MVP includes two explicit commercial isolation checks:

- `corepack pnpm verify:phase2`: validates RLS, creates a temporary foreign tenant inside a rolled-back transaction and verifies that a normal authenticated user cannot see it or its unassigned device/event/metric/insight rows.
- `corepack pnpm demo:validate`: logs in as each demo profile and verifies that hierarchy names and device owners stay inside the expected reporting tree.
