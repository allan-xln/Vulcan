do $$
begin
  if not exists (
    select 1 from pg_type where typname = 'daily_metric_run_status'
  ) then
    create type public.daily_metric_run_status as enum ('running', 'completed', 'failed');
  end if;
end
$$;

create table if not exists public.daily_metric_runs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references public.tenants (id) on delete cascade,
  metric_date date,
  started_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz,
  run_status public.daily_metric_run_status not null default 'running',
  metric_row_count integer not null default 0 check (metric_row_count >= 0),
  error_message text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null
);

create table if not exists public.daily_user_operational_metrics (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  metric_date date not null,
  workstation_id uuid references public.workstations (id) on delete set null,
  username text,
  session_slice_count integer not null default 0 check (session_slice_count >= 0),
  idle_window_count integer not null default 0 check (idle_window_count >= 0),
  application_usage_count integer not null default 0 check (application_usage_count >= 0),
  session_time_seconds integer not null default 0 check (session_time_seconds >= 0),
  idle_time_seconds integer not null default 0 check (idle_time_seconds >= 0),
  focused_app_usage_seconds integer not null default 0 check (focused_app_usage_seconds >= 0),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique nulls not distinct (tenant_id, metric_date, workstation_id, username)
);

create index if not exists idx_daily_metric_runs_tenant_date on public.daily_metric_runs (tenant_id, metric_date, started_at desc);
create index if not exists idx_daily_user_operational_metrics_tenant_date
  on public.daily_user_operational_metrics (tenant_id, metric_date desc, workstation_id);

grant select on public.daily_metric_runs to authenticated;
grant select on public.daily_user_operational_metrics to authenticated;
grant all privileges on public.daily_metric_runs to service_role;
grant all privileges on public.daily_user_operational_metrics to service_role;

alter table public.daily_metric_runs enable row level security;
alter table public.daily_user_operational_metrics enable row level security;

drop policy if exists daily_metric_runs_read_member on public.daily_metric_runs;
create policy daily_metric_runs_read_member
on public.daily_metric_runs
for select
to authenticated
using (tenant_id is null or public.is_tenant_member(tenant_id));

drop policy if exists daily_user_operational_metrics_read_member on public.daily_user_operational_metrics;
create policy daily_user_operational_metrics_read_member
on public.daily_user_operational_metrics
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop trigger if exists trg_daily_metric_runs_set_audit_fields on public.daily_metric_runs;
create trigger trg_daily_metric_runs_set_audit_fields
before insert or update on public.daily_metric_runs
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_daily_user_operational_metrics_set_audit_fields on public.daily_user_operational_metrics;
create trigger trg_daily_user_operational_metrics_set_audit_fields
before insert or update on public.daily_user_operational_metrics
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_daily_user_operational_metrics_audit on public.daily_user_operational_metrics;
create trigger trg_daily_user_operational_metrics_audit
after insert or update or delete on public.daily_user_operational_metrics
for each row execute function app_private.write_audit_log();

