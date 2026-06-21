# Database

## Database Strategy

Vulcan uses a single Supabase PostgreSQL database for all tenants.

The schema lives in `database/supabase`.

## Migration Areas

- SaaS hierarchy foundation: tenants, departments, roles, user profiles, memberships, membership closure, devices, events, metrics, insights, notifications, provider configs, audit logs.
- Transactional foundation: tenants, memberships, roles, permissions, org hierarchy, employees, workstations, agent installations, policies, feature flags, usage, audit logs.
- Ingestion: tenant-scoped ingestion API keys and raw operational event intake.
- Normalization: deterministic normalized operational events.
- Operational facts: session slices, idle windows, application usage facts.
- Daily metrics: daily user operational metrics.
- Root WhatsApp channel: templates, schedules, delivery queue and delivery logs.

## Tenant Columns

Business tables must include `tenant_id`. Global reference tables, such as subscription plan definitions and permission definitions, are the exception because they do not store tenant business data.

Run tables now require `tenant_id`; cross-tenant processing must be implemented as fan-out orchestration over tenant-specific jobs.

## Important Tables

- `tenants`
- `departments`
- `tenant_settings`
- `memberships`
- `membership_closure`
- `roles`
- `role_permissions`
- `employee_profiles`
- `workstations`
- `agent_installations`
- `operational_event_policies`
- `ingestion_api_keys`
- `raw_operational_event_intake`
- `normalized_operational_events`
- `session_slices`
- `idle_windows`
- `application_usage_facts`
- `daily_user_operational_metrics`
- `root_whatsapp_templates`
- `notification_schedules`
- `whatsapp_delivery_queue`
- `whatsapp_delivery_logs`
- `audit_logs`

## Hierarchy

The definitive dynamic hierarchy model is:

- `memberships.direct_manager_membership_id`: direct reporting line.
- `membership_closure`: generated ancestor/descendant table for infinite-depth authorization.

This supports Director -> Manager -> Supervisor -> Operator, CEO -> VP -> Director, or any tenant-defined structure without hard-coded levels.

## Root WhatsApp Channel

`root_whatsapp_templates` stores global or tenant-specific templates without secrets.

`notification_schedules` stores recurrence rules by tenant. Supported recurrence values are `imediato`, `diario`, `semanal`, `mensal` and `personalizado`.

`whatsapp_delivery_queue` stores one row per recipient/message, with `tenant_id`, `recipient_membership_id`, retry counters, provider result, scheduled time and final status.

`whatsapp_delivery_logs` stores every delivery attempt. Logs never store access tokens or provider secrets.

RLS allows tenant-scope users to see the tenant queue and hierarchy users to see only their own/subtree delivery records. Writes are performed by the backend service role after API authorization.

## Validation

Local validation scripts live in `scripts/verify-phase*.sh`. They remain as compatibility names for existing checks, but the official product language is Vulcan foundation validation.

## MVP Demo Seed

Run:

```bash
corepack pnpm seed:demo
```

The seed creates:

- tenant: `Vulcan Demo`
- Supabase Auth admin
- departments: Operacoes, Financeiro, Suporte
- roles: tenant admin, hierarchy manager, individual member
- hierarchy: Diretor Operacional -> Coordenador -> Gerente -> Supervisor -> Operador 1/2/3
- devices, activity events, operational metrics, insights, notifications, preferences, AI provider configs, and audit logs

`membership_closure` is recalculated after hierarchy writes and is validated by the seed flow.
