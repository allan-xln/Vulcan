# Supabase

Supabase is the primary Vulcan platform layer.

## Responsibilities

- Auth: production user identity.
- PostgreSQL: single multi-tenant database.
- RLS: database-level tenant and hierarchy isolation.
- Storage: tenant assets, exports, generated reports, and future agent artifacts.
- Realtime: optional live dashboard updates.
- Edge Functions: optional webhook and notification glue.

## Configured Locally

The project expects Supabase credentials in `.env` only. `.env.example` contains placeholders and must remain safe to commit.

Required variables:

```env
AUTH_PROVIDER=supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_DEMO_TENANT_ID=
NEXT_PUBLIC_DEMO_ADMIN_EMAIL=
NEXT_PUBLIC_DEMO_ADMIN_PASSWORD=
SUPABASE_URL=
SUPABASE_REST_URL=
SUPABASE_PROJECT_REF=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_SECRET_KEY=
DATABASE_URL=
DIRECT_DATABASE_URL=
SUPABASE_DEMO_ADMIN_EMAIL=
SUPABASE_DEMO_ADMIN_PASSWORD=
AGENT_ENROLLMENT_TOKEN=
```

## Backend Integration

`backend/api` exposes:

- `GET /supabase/status`
- Supabase Auth token validation for non-local bearer tokens.
- Local `admin/admin` fallback for development only when `MOCK_AUTH=true`.
- Real repository reads and writes through Supabase PostgreSQL with tenant and hierarchy filters.

Production APIs must validate the Supabase user, resolve the active membership, resolve `tenant_id`, and enforce hierarchy-aware authorization before reading business data.

## Frontend Auth

`frontend/web` uses `@supabase/supabase-js` with only public browser variables:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` or `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`

The frontend never uses service-role, secret keys, database passwords, or admin keys. Auth sessions persist in the browser and the Supabase access token is sent to the backend as `Authorization: Bearer <token>` with the active `X-Tenant-Id`.

## Demo Admin Seed

Create or refresh the demo admin and tenant data:

```bash
corepack pnpm seed:demo
```

Default local demo identity:

```text
email: admin@vulcan.local
password: VulcanAdmin123!
```

Override it before running the seed:

```bash
SUPABASE_DEMO_ADMIN_EMAIL=admin@company.test SUPABASE_DEMO_ADMIN_PASSWORD='change-me' corepack pnpm seed:demo
```

## Database Model

The migration `database/supabase/migrations/20260603000100_vulcan_saas_hierarchy_supabase.sql` defines the SaaS foundation:

- `tenants`
- `departments`
- `roles`
- `user_profiles`
- `memberships`
- `membership_closure`
- `devices`
- `activity_events`
- `operational_metrics`
- `ai_insights`
- `notifications`
- `notification_preferences`
- `ai_provider_configs`
- `audit_logs`

`membership_closure` is the key hierarchy table. It allows any depth of organizational reporting lines and enables queries such as "show me myself and everyone below me".

## Storage

The MVP migration provisions these buckets:

- `tenant-assets`
- `user-avatars`
- `reports`
- `exports`
- `agent-packages`

Hosted Supabase owns `storage.objects`, so object policies must be finalized in the Supabase Dashboard or Supabase CLI with owner-level privileges. Recommended path convention:

```text
<tenant_id>/<resource-id>/<filename>
```

Recommended policies:

- private buckets require authenticated users whose active membership belongs to the path tenant.
- `user-avatars` can be public for reads, but writes must still be tenant/user scoped.
- `agent-packages` writes are backend/service-only.
- `reports` and `exports` reads require tenant scope or descendant scope where applicable.

## RLS Strategy

RLS policies enforce:

- root Vulcan users can access all tenants.
- tenant admins can access all data inside one tenant.
- managers can access their own data and descendants.
- users can access only themselves.
- service role can run backend workflows but must be tightly guarded.

## Commands

Validate the configured Supabase project:

```bash
corepack pnpm supabase:validate
```

Apply migrations:

```bash
corepack pnpm supabase:migrate
```

## Connectivity Note

Some hosted Supabase direct database hosts resolve to IPv6 first or IPv6-only from certain networks. If `DATABASE_URL` fails locally with `Network is unreachable` while REST/Auth works, use the Supabase connection pooler string that supports your network, or enable IPv6/NAT64 on the machine running the backend.

The Windows agent is resilient to this condition: it keeps a local offline queue and retries heartbeat/sync when the backend/database becomes reachable again.

## Production Notes

Because credentials were shared in chat, rotate all Supabase keys before production. Keep service-role and secret keys only in backend runtime secrets.
