create extension if not exists pgcrypto;
create extension if not exists citext;

create schema if not exists app_private;

do $$
begin
  if not exists (
    select 1 from pg_type where typname = 'membership_status'
  ) then
    create type public.membership_status as enum ('pending', 'active', 'suspended', 'revoked');
  end if;

  if not exists (
    select 1 from pg_type where typname = 'org_node_type'
  ) then
    create type public.org_node_type as enum ('company', 'division', 'department', 'team', 'site', 'cost_center');
  end if;

  if not exists (
    select 1 from pg_type where typname = 'employment_status'
  ) then
    create type public.employment_status as enum ('active', 'inactive', 'leave', 'contractor');
  end if;

  if not exists (
    select 1 from pg_type where typname = 'workstation_os_family'
  ) then
    create type public.workstation_os_family as enum ('windows', 'macos', 'linux');
  end if;

  if not exists (
    select 1 from pg_type where typname = 'agent_installation_status'
  ) then
    create type public.agent_installation_status as enum ('pending', 'active', 'disabled', 'retired');
  end if;

  if not exists (
    select 1 from pg_type where typname = 'billing_interval'
  ) then
    create type public.billing_interval as enum ('monthly', 'yearly');
  end if;
end
$$;

create table if not exists public.subscription_plans (
  id uuid primary key default gen_random_uuid(),
  plan_key text not null unique,
  name text not null,
  description text,
  billing_interval public.billing_interval not null default 'monthly',
  price_cents integer not null check (price_cents >= 0),
  included_members integer not null default 0 check (included_members >= 0),
  included_workstations integer not null default 0 check (included_workstations >= 0),
  included_monthly_events bigint not null default 0 check (included_monthly_events >= 0),
  features jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create table if not exists public.tenants (
  id uuid primary key default gen_random_uuid(),
  subscription_plan_id uuid references public.subscription_plans (id) on delete set null,
  slug text not null unique,
  legal_name text not null,
  display_name text not null,
  billing_email citext,
  status text not null default 'active' check (status in ('active', 'trial', 'suspended', 'disabled')),
  country_code text check (country_code is null or char_length(country_code) = 2),
  timezone text not null default 'UTC',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create table if not exists public.tenant_settings (
  tenant_id uuid primary key references public.tenants (id) on delete cascade,
  default_locale text not null default 'en-US',
  default_timezone text not null default 'UTC',
  retention_days integer not null default 30 check (retention_days > 0),
  allow_self_service_agent_installation boolean not null default false,
  analytics_enabled boolean not null default true,
  ai_explanations_enabled boolean not null default true,
  settings jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create table if not exists public.user_profiles (
  user_id uuid primary key references auth.users (id) on delete cascade,
  primary_email citext,
  display_name text,
  avatar_url text,
  locale text default 'en-US',
  timezone text default 'UTC',
  last_seen_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.permissions (
  id uuid primary key default gen_random_uuid(),
  permission_key text not null unique,
  name text not null,
  description text not null,
  resource text not null,
  action text not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create table if not exists public.roles (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  slug text not null,
  name text not null,
  description text,
  is_system boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (tenant_id, slug)
);

create table if not exists public.role_permissions (
  id uuid primary key default gen_random_uuid(),
  role_id uuid not null references public.roles (id) on delete cascade,
  permission_id uuid not null references public.permissions (id) on delete cascade,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (role_id, permission_id)
);

create table if not exists public.memberships (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role_id uuid not null references public.roles (id) on delete restrict,
  status public.membership_status not null default 'pending',
  invited_by uuid references auth.users (id) on delete set null,
  joined_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (tenant_id, user_id)
);

create table if not exists public.org_nodes (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  node_key text not null,
  name text not null,
  node_type public.org_node_type not null,
  description text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (tenant_id, node_key)
);

create table if not exists public.org_edges (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  parent_node_id uuid not null references public.org_nodes (id) on delete cascade,
  child_node_id uuid not null references public.org_nodes (id) on delete cascade,
  edge_type text not null default 'primary' check (edge_type in ('primary', 'secondary')),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (tenant_id, parent_node_id, child_node_id),
  check (parent_node_id <> child_node_id)
);

create table if not exists public.org_closure (
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  ancestor_node_id uuid not null references public.org_nodes (id) on delete cascade,
  descendant_node_id uuid not null references public.org_nodes (id) on delete cascade,
  depth integer not null check (depth >= 0),
  created_at timestamptz not null default timezone('utc', now()),
  primary key (tenant_id, ancestor_node_id, descendant_node_id)
);

create table if not exists public.employee_profiles (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  membership_id uuid unique references public.memberships (id) on delete set null,
  org_node_id uuid references public.org_nodes (id) on delete set null,
  employee_number text,
  full_name text not null,
  work_email citext,
  employment_status public.employment_status not null default 'active',
  title text,
  start_date date,
  end_date date,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create table if not exists public.workstations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  employee_profile_id uuid references public.employee_profiles (id) on delete set null,
  hostname text not null,
  os_family public.workstation_os_family not null,
  serial_number text,
  device_fingerprint text not null,
  enrolled_at timestamptz not null default timezone('utc', now()),
  last_seen_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (tenant_id, device_fingerprint)
);

create table if not exists public.agent_installations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  workstation_id uuid not null references public.workstations (id) on delete cascade,
  installation_key_hash text not null unique,
  agent_version text not null,
  osquery_version text,
  status public.agent_installation_status not null default 'pending',
  last_check_in_at timestamptz,
  approved_by uuid references auth.users (id) on delete set null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create table if not exists public.telemetry_policies (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  policy_key text not null,
  name text not null,
  description text,
  is_enabled boolean not null default true,
  policy_payload jsonb not null default '{}'::jsonb,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (tenant_id, policy_key)
);

create table if not exists public.feature_flags (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  flag_key text not null,
  name text not null,
  description text,
  enabled boolean not null default false,
  variant text,
  rollout_rules jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (tenant_id, flag_key)
);

create table if not exists public.tenant_usage (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  period_start date not null,
  period_end date not null,
  active_member_count integer not null default 0 check (active_member_count >= 0),
  active_workstation_count integer not null default 0 check (active_workstation_count >= 0),
  telemetry_event_count bigint not null default 0 check (telemetry_event_count >= 0),
  ai_explanation_count bigint not null default 0 check (ai_explanation_count >= 0),
  storage_bytes bigint not null default 0 check (storage_bytes >= 0),
  usage_payload jsonb not null default '{}'::jsonb,
  calculated_at timestamptz not null default timezone('utc', now()),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (tenant_id, period_start, period_end),
  check (period_end >= period_start)
);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  actor_user_id uuid references auth.users (id) on delete set null,
  actor_membership_id uuid references public.memberships (id) on delete set null,
  action text not null,
  entity_table text not null,
  entity_id uuid,
  change_summary jsonb not null default '{}'::jsonb,
  request_context jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_tenants_subscription_plan_id on public.tenants (subscription_plan_id);
create index if not exists idx_roles_tenant_id on public.roles (tenant_id);
create index if not exists idx_memberships_tenant_id on public.memberships (tenant_id);
create index if not exists idx_memberships_user_id on public.memberships (user_id);
create index if not exists idx_memberships_role_id on public.memberships (role_id);
create index if not exists idx_role_permissions_role_id on public.role_permissions (role_id);
create index if not exists idx_role_permissions_permission_id on public.role_permissions (permission_id);
create index if not exists idx_org_nodes_tenant_id on public.org_nodes (tenant_id);
create index if not exists idx_org_edges_tenant_parent on public.org_edges (tenant_id, parent_node_id);
create index if not exists idx_org_edges_tenant_child on public.org_edges (tenant_id, child_node_id);
create index if not exists idx_org_closure_tenant_ancestor on public.org_closure (tenant_id, ancestor_node_id, depth);
create index if not exists idx_org_closure_tenant_descendant on public.org_closure (tenant_id, descendant_node_id, depth);
create index if not exists idx_employee_profiles_tenant_id on public.employee_profiles (tenant_id);
create unique index if not exists idx_employee_profiles_tenant_employee_number
  on public.employee_profiles (tenant_id, employee_number)
  where employee_number is not null;
create index if not exists idx_workstations_tenant_id on public.workstations (tenant_id);
create index if not exists idx_workstations_employee_profile_id on public.workstations (employee_profile_id);
create index if not exists idx_agent_installations_tenant_id on public.agent_installations (tenant_id);
create index if not exists idx_agent_installations_workstation_id on public.agent_installations (workstation_id);
create index if not exists idx_telemetry_policies_tenant_id on public.telemetry_policies (tenant_id);
create index if not exists idx_feature_flags_tenant_id on public.feature_flags (tenant_id);
create index if not exists idx_tenant_usage_tenant_id on public.tenant_usage (tenant_id, period_start desc);
create index if not exists idx_audit_logs_tenant_id on public.audit_logs (tenant_id, created_at desc);
create index if not exists idx_audit_logs_entity on public.audit_logs (entity_table, entity_id, created_at desc);
create index if not exists idx_audit_logs_actor_user_id on public.audit_logs (actor_user_id, created_at desc);

grant usage on schema public to anon, authenticated, service_role;

grant select on public.subscription_plans to authenticated;
grant select, insert, update, delete on public.tenants to authenticated;
grant select, insert, update, delete on public.tenant_settings to authenticated;
grant select, insert, update, delete on public.user_profiles to authenticated;
grant select on public.permissions to authenticated;
grant select, insert, update, delete on public.roles to authenticated;
grant select, insert, update, delete on public.role_permissions to authenticated;
grant select, insert, update, delete on public.memberships to authenticated;
grant select, insert, update, delete on public.org_nodes to authenticated;
grant select, insert, update, delete on public.org_edges to authenticated;
grant select on public.org_closure to authenticated;
grant select, insert, update, delete on public.employee_profiles to authenticated;
grant select, insert, update, delete on public.workstations to authenticated;
grant select, insert, update, delete on public.agent_installations to authenticated;
grant select, insert, update, delete on public.telemetry_policies to authenticated;
grant select, insert, update, delete on public.feature_flags to authenticated;
grant select on public.audit_logs to authenticated;
grant select, insert, update, delete on public.tenant_usage to authenticated;

grant all privileges on all tables in schema public to service_role;
