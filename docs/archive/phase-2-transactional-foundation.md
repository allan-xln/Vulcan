# Phase 2 Transactional Foundation

## Goal
Implement the Supabase/Postgres control-plane schema for multi-tenant SaaS isolation, tenant membership, hierarchy support and auditability.

## Design choices
- Tenant isolation: every tenant-owned table carries `tenant_id` and is protected by RLS through membership-aware helper functions.
- Identity: `auth.users` is the identity source; `public.user_profiles` extends it without duplicating authentication data.
- Hierarchy: `org_edges` stores adjacency and `org_closure` stores transitive paths for efficient ancestry and descendant queries.
- Audit: `audit_logs` is append-only and is populated by generic triggers on tenant-scoped tables.
- Authorization: `roles`, `permissions` and `role_permissions` provide explicit authorization data, while initial RLS uses `owner` and `admin` role slugs for management operations.

## Tables
- `subscription_plans`: global plan catalog.
- `tenants`: tenant root entity and billing/context metadata.
- `tenant_settings`: one-to-one tenant configuration.
- `user_profiles`: one-to-one extension of Supabase Auth users.
- `permissions`: global permission catalog.
- `roles`: tenant-scoped roles.
- `role_permissions`: tenant role to global permission mapping.
- `memberships`: user-to-tenant membership and assigned role.
- `org_nodes`: hierarchy nodes.
- `org_edges`: adjacency edges.
- `org_closure`: materialized hierarchy closure for fast traversal.
- `employee_profiles`: tenant employee/person records.
- `workstations`: managed workstation inventory.
- `agent_installations`: tenant-approved local agent installations.
- `operational_event_policies`: tenant-specific allowed telemetry policies.
- `feature_flags`: tenant-level feature rollout state.
- `tenant_usage`: periodized usage rollups.
- `audit_logs`: append-only audit trail.

## Local seed behavior
- Global catalogs and one sample tenant are always seeded.
- If at least one `auth.users` row exists locally, the first user is linked into `user_profiles` and granted the seeded `owner` membership for the sample tenant.
- No fake auth rows are inserted by the seed.

## RLS baseline
- Tenant members can read tenant-scoped rows for their tenant.
- Owners and admins can manage tenant-scoped configuration and membership rows.
- `user_profiles` is self-scoped by `auth.uid()`.
- Global catalog tables remain read-only for authenticated users.

