do $$
begin
  if not exists (
    select 1 from pg_type where typname = 'operational_fact_run_status'
  ) then
    create type public.operational_fact_run_status as enum ('running', 'completed', 'failed');
  end if;
end
$$;

create table if not exists public.operational_fact_runs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  started_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz,
  run_status public.operational_fact_run_status not null default 'running',
  session_slice_count integer not null default 0 check (session_slice_count >= 0),
  idle_window_count integer not null default 0 check (idle_window_count >= 0),
  application_usage_count integer not null default 0 check (application_usage_count >= 0),
  error_message text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create table if not exists public.session_slices (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  workstation_id uuid references public.workstations (id) on delete set null,
  agent_installation_id uuid references public.agent_installations (id) on delete set null,
  session_id text not null,
  username text,
  start_normalized_event_id uuid not null unique references public.normalized_operational_events (id) on delete cascade,
  end_normalized_event_id uuid references public.normalized_operational_events (id) on delete set null,
  started_at timestamptz not null,
  ended_at timestamptz,
  duration_seconds integer check (duration_seconds is null or duration_seconds >= 0),
  start_event_type text not null,
  end_event_type text,
  closure_reason text not null,
  is_open boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create table if not exists public.idle_windows (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  workstation_id uuid references public.workstations (id) on delete set null,
  agent_installation_id uuid references public.agent_installations (id) on delete set null,
  session_id text not null,
  start_normalized_event_id uuid not null unique references public.normalized_operational_events (id) on delete cascade,
  end_normalized_event_id uuid references public.normalized_operational_events (id) on delete set null,
  started_at timestamptz not null,
  ended_at timestamptz,
  duration_seconds integer check (duration_seconds is null or duration_seconds >= 0),
  idle_threshold_seconds integer,
  closure_reason text not null,
  is_open boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create table if not exists public.application_usage_facts (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  workstation_id uuid references public.workstations (id) on delete set null,
  agent_installation_id uuid references public.agent_installations (id) on delete set null,
  session_id text,
  app_name text not null,
  process_name text,
  focus_start_normalized_event_id uuid not null unique references public.normalized_operational_events (id) on delete cascade,
  focus_end_normalized_event_id uuid references public.normalized_operational_events (id) on delete set null,
  started_at timestamptz not null,
  ended_at timestamptz,
  duration_seconds integer check (duration_seconds is null or duration_seconds >= 0),
  end_reason text not null,
  is_open boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create index if not exists idx_operational_fact_runs_tenant on public.operational_fact_runs (tenant_id, started_at desc);
create index if not exists idx_session_slices_tenant_time on public.session_slices (tenant_id, started_at desc);
create index if not exists idx_idle_windows_tenant_time on public.idle_windows (tenant_id, started_at desc);
create index if not exists idx_application_usage_facts_tenant_time on public.application_usage_facts (tenant_id, started_at desc);
create index if not exists idx_application_usage_facts_tenant_app on public.application_usage_facts (tenant_id, app_name, started_at desc);

grant select on public.operational_fact_runs to authenticated;
grant select on public.session_slices to authenticated;
grant select on public.idle_windows to authenticated;
grant select on public.application_usage_facts to authenticated;
grant all privileges on public.operational_fact_runs to service_role;
grant all privileges on public.session_slices to service_role;
grant all privileges on public.idle_windows to service_role;
grant all privileges on public.application_usage_facts to service_role;

alter table public.operational_fact_runs enable row level security;
alter table public.session_slices enable row level security;
alter table public.idle_windows enable row level security;
alter table public.application_usage_facts enable row level security;

drop policy if exists operational_fact_runs_read_member on public.operational_fact_runs;
create policy operational_fact_runs_read_member
on public.operational_fact_runs
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists session_slices_read_member on public.session_slices;
create policy session_slices_read_member
on public.session_slices
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists idle_windows_read_member on public.idle_windows;
create policy idle_windows_read_member
on public.idle_windows
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists application_usage_facts_read_member on public.application_usage_facts;
create policy application_usage_facts_read_member
on public.application_usage_facts
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop trigger if exists trg_operational_fact_runs_set_audit_fields on public.operational_fact_runs;
create trigger trg_operational_fact_runs_set_audit_fields
before insert or update on public.operational_fact_runs
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_session_slices_set_audit_fields on public.session_slices;
create trigger trg_session_slices_set_audit_fields
before insert or update on public.session_slices
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_idle_windows_set_audit_fields on public.idle_windows;
create trigger trg_idle_windows_set_audit_fields
before insert or update on public.idle_windows
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_application_usage_facts_set_audit_fields on public.application_usage_facts;
create trigger trg_application_usage_facts_set_audit_fields
before insert or update on public.application_usage_facts
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_session_slices_audit on public.session_slices;
create trigger trg_session_slices_audit
after insert or update or delete on public.session_slices
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_idle_windows_audit on public.idle_windows;
create trigger trg_idle_windows_audit
after insert or update or delete on public.idle_windows
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_application_usage_facts_audit on public.application_usage_facts;
create trigger trg_application_usage_facts_audit
after insert or update or delete on public.application_usage_facts
for each row execute function app_private.write_audit_log();

