do $$
begin
  if not exists (
    select 1 from pg_type where typname = 'normalization_run_status'
  ) then
    create type public.normalization_run_status as enum ('running', 'completed', 'failed');
  end if;
end
$$;

create table if not exists public.normalization_runs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  started_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz,
  run_status public.normalization_run_status not null default 'running',
  processed_count integer not null default 0 check (processed_count >= 0),
  duplicate_count integer not null default 0 check (duplicate_count >= 0),
  error_message text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create table if not exists public.normalized_operational_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  raw_operational_event_intake_id uuid not null unique references public.raw_operational_event_intake (id) on delete cascade,
  source_event_id uuid not null,
  workstation_id uuid references public.workstations (id) on delete set null,
  agent_installation_id uuid references public.agent_installations (id) on delete set null,
  normalized_event_type text not null,
  schema_version text not null,
  occurred_at timestamptz not null,
  received_at timestamptz not null,
  normalized_at timestamptz not null default timezone('utc', now()),
  session_id text,
  username text,
  app_name text,
  process_name text,
  queue_depth integer,
  idle_threshold_seconds integer,
  normalized_payload jsonb not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (tenant_id, source_event_id)
);

create index if not exists idx_normalization_runs_tenant_id on public.normalization_runs (tenant_id, started_at desc);
create index if not exists idx_normalized_operational_events_tenant_time
  on public.normalized_operational_events (tenant_id, occurred_at desc);
create index if not exists idx_normalized_operational_events_type
  on public.normalized_operational_events (tenant_id, normalized_event_type, occurred_at desc);
create index if not exists idx_normalized_operational_events_workstation
  on public.normalized_operational_events (tenant_id, workstation_id, occurred_at desc);

grant select on public.normalized_operational_events to authenticated;
grant select on public.normalization_runs to authenticated;
grant all privileges on public.normalized_operational_events to service_role;
grant all privileges on public.normalization_runs to service_role;

alter table public.normalization_runs enable row level security;
alter table public.normalized_operational_events enable row level security;

drop policy if exists normalization_runs_read_member on public.normalization_runs;
create policy normalization_runs_read_member
on public.normalization_runs
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists normalized_operational_events_read_member on public.normalized_operational_events;
create policy normalized_operational_events_read_member
on public.normalized_operational_events
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop trigger if exists trg_normalization_runs_set_audit_fields on public.normalization_runs;
create trigger trg_normalization_runs_set_audit_fields
before insert or update on public.normalization_runs
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_normalized_operational_events_set_audit_fields on public.normalized_operational_events;
create trigger trg_normalized_operational_events_set_audit_fields
before insert or update on public.normalized_operational_events
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_normalized_operational_events_audit on public.normalized_operational_events;
create trigger trg_normalized_operational_events_audit
after insert or update or delete on public.normalized_operational_events
for each row execute function app_private.write_audit_log();
