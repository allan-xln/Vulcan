create extension if not exists pgcrypto;
create extension if not exists citext;

do $$
begin
  if not exists (select 1 from pg_type where typname = 'vulcan_membership_status') then
    create type public.vulcan_membership_status as enum ('pending', 'active', 'suspended', 'revoked');
  end if;

  if not exists (select 1 from pg_type where typname = 'vulcan_notification_channel') then
    create type public.vulcan_notification_channel as enum ('system', 'push', 'windows', 'whatsapp', 'email');
  end if;

  if not exists (select 1 from pg_type where typname = 'vulcan_notification_status') then
    create type public.vulcan_notification_status as enum ('queued', 'sent', 'failed', 'mocked', 'missing_credentials', 'disabled');
  end if;

  if not exists (select 1 from pg_type where typname = 'vulcan_insight_impact') then
    create type public.vulcan_insight_impact as enum ('low', 'medium', 'high', 'critical');
  end if;

  if not exists (select 1 from pg_type where typname = 'vulcan_ai_route') then
    create type public.vulcan_ai_route as enum ('rules', 'llama', 'gpt');
  end if;
end
$$;

create table if not exists public.vulcan_root_users (
  user_id uuid primary key references auth.users (id) on delete cascade,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.tenants (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  legal_name text,
  display_name text not null,
  region text not null default 'global',
  plan text not null default 'growth',
  status text not null default 'active' check (status in ('trial', 'active', 'suspended', 'disabled')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.departments (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  parent_department_id uuid references public.departments (id) on delete set null,
  name text not null,
  slug text not null,
  description text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, slug)
);

create table if not exists public.roles (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references public.tenants (id) on delete cascade,
  slug text not null,
  name text not null,
  description text,
  scope text not null default 'tenant' check (scope in ('self', 'hierarchy', 'tenant', 'global')),
  is_system boolean not null default false,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, slug)
);

alter table public.roles add column if not exists scope text not null default 'tenant';
alter table public.roles add column if not exists is_system boolean not null default false;

create table if not exists public.user_profiles (
  user_id uuid primary key references auth.users (id) on delete cascade,
  primary_email citext,
  display_name text,
  avatar_url text,
  locale text default 'pt-BR',
  timezone text default 'America/Sao_Paulo',
  last_seen_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.memberships (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  role_id uuid references public.roles (id) on delete set null,
  department_id uuid references public.departments (id) on delete set null,
  direct_manager_membership_id uuid references public.memberships (id) on delete set null,
  status public.vulcan_membership_status not null default 'pending',
  full_name text not null,
  work_email citext,
  phone text,
  whatsapp text,
  title text,
  hierarchy_level integer,
  joined_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, user_id),
  check (direct_manager_membership_id is null or direct_manager_membership_id <> id)
);

alter table public.memberships add column if not exists department_id uuid references public.departments (id) on delete set null;
alter table public.memberships add column if not exists direct_manager_membership_id uuid references public.memberships (id) on delete set null;
alter table public.memberships add column if not exists full_name text;
alter table public.memberships add column if not exists work_email citext;
alter table public.memberships add column if not exists phone text;
alter table public.memberships add column if not exists whatsapp text;
alter table public.memberships add column if not exists title text;
alter table public.memberships add column if not exists hierarchy_level integer;

update public.memberships
set full_name = coalesce(full_name, metadata ->> 'full_name', user_id::text)
where full_name is null;

create table if not exists public.membership_closure (
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  ancestor_membership_id uuid not null references public.memberships (id) on delete cascade,
  descendant_membership_id uuid not null references public.memberships (id) on delete cascade,
  depth integer not null check (depth >= 0),
  created_at timestamptz not null default timezone('utc', now()),
  primary key (tenant_id, ancestor_membership_id, descendant_membership_id)
);

create table if not exists public.devices (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  owner_membership_id uuid references public.memberships (id) on delete set null,
  hostname text not null,
  os text not null,
  device_fingerprint text not null,
  status text not null default 'pending' check (status in ('pending', 'online', 'offline', 'syncing', 'retired')),
  last_seen_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, device_fingerprint)
);

create table if not exists public.activity_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  membership_id uuid references public.memberships (id) on delete set null,
  device_id uuid references public.devices (id) on delete set null,
  source_event_id text,
  event_type text not null,
  app_name text,
  window_title text,
  category text,
  duration_seconds integer check (duration_seconds is null or duration_seconds >= 0),
  occurred_at timestamptz not null,
  llama_classification jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.operational_metrics (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  membership_id uuid references public.memberships (id) on delete set null,
  department_id uuid references public.departments (id) on delete set null,
  metric_key text not null,
  metric_label text not null,
  value_numeric numeric,
  value_text text,
  period_start timestamptz not null,
  period_end timestamptz not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  check (period_end >= period_start)
);

create table if not exists public.ai_insights (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  membership_id uuid references public.memberships (id) on delete set null,
  department_id uuid references public.departments (id) on delete set null,
  source_route public.vulcan_ai_route not null default 'rules',
  source_model text,
  title text not null,
  summary text not null,
  recommendation text,
  impact public.vulcan_insight_impact not null default 'medium',
  automation_savings_hours numeric,
  confidence numeric check (confidence is null or (confidence >= 0 and confidence <= 1)),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  recipient_membership_id uuid references public.memberships (id) on delete set null,
  channel public.vulcan_notification_channel not null,
  notification_type text not null,
  status public.vulcan_notification_status not null default 'queued',
  title text not null,
  message text not null,
  provider text,
  provider_message_id text,
  sent_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.notification_preferences (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  membership_id uuid not null references public.memberships (id) on delete cascade,
  channel public.vulcan_notification_channel not null,
  notification_type text not null,
  enabled boolean not null default true,
  quiet_hours jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, membership_id, channel, notification_type)
);

create table if not exists public.ai_provider_configs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references public.tenants (id) on delete cascade,
  provider text not null check (provider in ('openai', 'ollama', 'openrouter', 'together', 'groq')),
  purpose text not null check (purpose in ('operational', 'executive', 'copilot')),
  model text not null,
  base_url text,
  secret_ref text,
  enabled boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references public.tenants (id) on delete cascade,
  actor_user_id uuid references auth.users (id) on delete set null,
  action text not null,
  resource_type text not null,
  resource_id uuid,
  ip_address inet,
  user_agent text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_departments_tenant_parent on public.departments (tenant_id, parent_department_id);
create index if not exists idx_memberships_tenant_manager on public.memberships (tenant_id, direct_manager_membership_id);
create index if not exists idx_membership_closure_descendant on public.membership_closure (tenant_id, descendant_membership_id);
create index if not exists idx_devices_tenant_owner on public.devices (tenant_id, owner_membership_id);
alter table public.activity_events add column if not exists source_event_id text;
create index if not exists idx_activity_events_tenant_occurred on public.activity_events (tenant_id, occurred_at desc);
create index if not exists idx_activity_events_tenant_member on public.activity_events (tenant_id, membership_id);
create unique index if not exists idx_activity_events_tenant_source_event
  on public.activity_events (tenant_id, source_event_id)
  where source_event_id is not null;
create index if not exists idx_operational_metrics_tenant_period on public.operational_metrics (tenant_id, period_start desc, period_end desc);
create index if not exists idx_ai_insights_tenant_created on public.ai_insights (tenant_id, created_at desc);
create index if not exists idx_notifications_tenant_recipient on public.notifications (tenant_id, recipient_membership_id, created_at desc);
create index if not exists idx_audit_logs_tenant_created on public.audit_logs (tenant_id, created_at desc);

create or replace function public.vulcan_is_root_user()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select auth.role() = 'service_role'
    or exists (
      select 1
      from public.vulcan_root_users root_user
      where root_user.user_id = auth.uid()
    );
$$;

create or replace function public.vulcan_is_tenant_member(p_tenant_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select public.vulcan_is_root_user()
    or exists (
      select 1
      from public.memberships membership
      where membership.tenant_id = p_tenant_id
        and membership.user_id = auth.uid()
        and membership.status = 'active'
    );
$$;

create or replace function public.vulcan_has_tenant_scope(p_tenant_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select public.vulcan_is_root_user()
    or exists (
      select 1
      from public.memberships membership
      join public.roles role on role.id = membership.role_id
      where membership.tenant_id = p_tenant_id
        and membership.user_id = auth.uid()
        and membership.status = 'active'
        and role.scope in ('tenant', 'global')
    );
$$;

create or replace function public.vulcan_current_membership_id(p_tenant_id uuid)
returns uuid
language sql
stable
security definer
set search_path = public
as $$
  select membership.id
  from public.memberships membership
  where membership.tenant_id = p_tenant_id
    and membership.user_id = auth.uid()
    and membership.status = 'active'
  limit 1;
$$;

create or replace function public.vulcan_can_view_membership(p_tenant_id uuid, p_target_membership_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select public.vulcan_has_tenant_scope(p_tenant_id)
    or exists (
      select 1
      from public.membership_closure closure_row
      where closure_row.tenant_id = p_tenant_id
        and closure_row.ancestor_membership_id = public.vulcan_current_membership_id(p_tenant_id)
        and closure_row.descendant_membership_id = p_target_membership_id
    );
$$;

create or replace function public.vulcan_refresh_membership_closure(p_tenant_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  delete from public.membership_closure where tenant_id = p_tenant_id;

  insert into public.membership_closure (
    tenant_id,
    ancestor_membership_id,
    descendant_membership_id,
    depth
  )
  with recursive hierarchy as (
    select
      membership.tenant_id,
      membership.id as ancestor_membership_id,
      membership.id as descendant_membership_id,
      0 as depth
    from public.memberships membership
    where membership.tenant_id = p_tenant_id

    union all

    select
      hierarchy.tenant_id,
      hierarchy.ancestor_membership_id,
      child.id as descendant_membership_id,
      hierarchy.depth + 1 as depth
    from hierarchy
    join public.memberships child
      on child.tenant_id = hierarchy.tenant_id
     and child.direct_manager_membership_id = hierarchy.descendant_membership_id
    where hierarchy.depth < 1000
  )
  select tenant_id, ancestor_membership_id, descendant_membership_id, depth
  from hierarchy
  on conflict do nothing;
end;
$$;

create or replace function public.vulcan_refresh_membership_closure_trigger()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if tg_op = 'DELETE' then
    perform public.vulcan_refresh_membership_closure(old.tenant_id);
    return old;
  end if;

  perform public.vulcan_refresh_membership_closure(new.tenant_id);
  return new;
end;
$$;

drop trigger if exists trg_vulcan_membership_closure_refresh on public.memberships;
create trigger trg_vulcan_membership_closure_refresh
after insert or update of direct_manager_membership_id, tenant_id or delete
on public.memberships
for each row execute function public.vulcan_refresh_membership_closure_trigger();

alter table public.tenants enable row level security;
alter table public.departments enable row level security;
alter table public.roles enable row level security;
alter table public.user_profiles enable row level security;
alter table public.memberships enable row level security;
alter table public.membership_closure enable row level security;
alter table public.devices enable row level security;
alter table public.activity_events enable row level security;
alter table public.operational_metrics enable row level security;
alter table public.ai_insights enable row level security;
alter table public.notifications enable row level security;
alter table public.notification_preferences enable row level security;
alter table public.ai_provider_configs enable row level security;
alter table public.audit_logs enable row level security;

drop policy if exists tenants_read_by_member on public.tenants;
create policy tenants_read_by_member on public.tenants
for select using (public.vulcan_is_tenant_member(id));

drop policy if exists tenant_tables_read_departments on public.departments;
create policy tenant_tables_read_departments on public.departments
for select using (public.vulcan_is_tenant_member(tenant_id));

drop policy if exists tenant_tables_read_roles on public.roles;
create policy tenant_tables_read_roles on public.roles
for select using (tenant_id is null or public.vulcan_is_tenant_member(tenant_id));

drop policy if exists profiles_read_self on public.user_profiles;
create policy profiles_read_self on public.user_profiles
for select using (public.vulcan_is_root_user() or user_id = auth.uid());

drop policy if exists memberships_read_hierarchy on public.memberships;
create policy memberships_read_hierarchy on public.memberships
for select using (public.vulcan_can_view_membership(tenant_id, id));

drop policy if exists membership_closure_read_member on public.membership_closure;
create policy membership_closure_read_member on public.membership_closure
for select using (public.vulcan_is_tenant_member(tenant_id));

drop policy if exists devices_read_hierarchy on public.devices;
create policy devices_read_hierarchy on public.devices
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or (public.vulcan_is_tenant_member(tenant_id) and owner_membership_id is null)
  or public.vulcan_can_view_membership(tenant_id, owner_membership_id)
);

drop policy if exists activity_events_read_hierarchy on public.activity_events;
create policy activity_events_read_hierarchy on public.activity_events
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or (public.vulcan_is_tenant_member(tenant_id) and membership_id is null)
  or public.vulcan_can_view_membership(tenant_id, membership_id)
);

drop policy if exists metrics_read_hierarchy on public.operational_metrics;
create policy metrics_read_hierarchy on public.operational_metrics
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or (public.vulcan_is_tenant_member(tenant_id) and membership_id is null)
  or public.vulcan_can_view_membership(tenant_id, membership_id)
);

drop policy if exists insights_read_hierarchy on public.ai_insights;
create policy insights_read_hierarchy on public.ai_insights
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or (public.vulcan_is_tenant_member(tenant_id) and membership_id is null)
  or public.vulcan_can_view_membership(tenant_id, membership_id)
);

drop policy if exists notifications_read_recipient_or_admin on public.notifications;
create policy notifications_read_recipient_or_admin on public.notifications
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or recipient_membership_id = public.vulcan_current_membership_id(tenant_id)
);

drop policy if exists notification_preferences_read_owner on public.notification_preferences;
create policy notification_preferences_read_owner on public.notification_preferences
for select using (
  public.vulcan_has_tenant_scope(tenant_id)
  or membership_id = public.vulcan_current_membership_id(tenant_id)
);

drop policy if exists ai_provider_configs_read_admin on public.ai_provider_configs;
create policy ai_provider_configs_read_admin on public.ai_provider_configs
for select using (tenant_id is null or public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists audit_logs_read_admin on public.audit_logs;
create policy audit_logs_read_admin on public.audit_logs
for select using (tenant_id is null or public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists service_role_all_tenants on public.tenants;
create policy service_role_all_tenants on public.tenants for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_departments on public.departments;
create policy service_role_all_departments on public.departments for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_roles on public.roles;
create policy service_role_all_roles on public.roles for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_user_profiles on public.user_profiles;
create policy service_role_all_user_profiles on public.user_profiles for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_memberships on public.memberships;
create policy service_role_all_memberships on public.memberships for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_membership_closure on public.membership_closure;
create policy service_role_all_membership_closure on public.membership_closure for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_devices on public.devices;
create policy service_role_all_devices on public.devices for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_activity_events on public.activity_events;
create policy service_role_all_activity_events on public.activity_events for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_operational_metrics on public.operational_metrics;
create policy service_role_all_operational_metrics on public.operational_metrics for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_ai_insights on public.ai_insights;
create policy service_role_all_ai_insights on public.ai_insights for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_notifications on public.notifications;
create policy service_role_all_notifications on public.notifications for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_notification_preferences on public.notification_preferences;
create policy service_role_all_notification_preferences on public.notification_preferences for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_ai_provider_configs on public.ai_provider_configs;
create policy service_role_all_ai_provider_configs on public.ai_provider_configs for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_audit_logs on public.audit_logs;
create policy service_role_all_audit_logs on public.audit_logs for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant select on public.departments to authenticated;
grant select on public.roles to authenticated;
grant select on public.user_profiles to authenticated;
grant select on public.memberships to authenticated;
grant select on public.membership_closure to authenticated;
grant select on public.devices to authenticated;
grant select on public.activity_events to authenticated;
grant select on public.operational_metrics to authenticated;
grant select on public.ai_insights to authenticated;
grant select on public.notifications to authenticated;
grant select on public.notification_preferences to authenticated;
grant select on public.ai_provider_configs to authenticated;
grant select on public.audit_logs to authenticated;

grant all privileges on public.departments to service_role;
grant all privileges on public.roles to service_role;
grant all privileges on public.user_profiles to service_role;
grant all privileges on public.memberships to service_role;
grant all privileges on public.membership_closure to service_role;
grant all privileges on public.devices to service_role;
grant all privileges on public.activity_events to service_role;
grant all privileges on public.operational_metrics to service_role;
grant all privileges on public.ai_insights to service_role;
grant all privileges on public.notifications to service_role;
grant all privileges on public.notification_preferences to service_role;
grant all privileges on public.ai_provider_configs to service_role;
grant all privileges on public.audit_logs to service_role;
