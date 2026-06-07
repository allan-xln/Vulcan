do $$
begin
  if not exists (
    select 1 from pg_type where typname = 'ingestion_key_status'
  ) then
    create type public.ingestion_key_status as enum ('active', 'disabled', 'revoked');
  end if;

  if not exists (
    select 1 from pg_type where typname = 'raw_intake_status'
  ) then
    create type public.raw_intake_status as enum ('pending', 'accepted', 'duplicate', 'rejected');
  end if;
end
$$;

create table if not exists public.ingestion_api_keys (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  name text not null,
  key_prefix text not null,
  key_hash text not null unique,
  status public.ingestion_key_status not null default 'active',
  scopes text[] not null default array['operational_events:ingest']::text[],
  expires_at timestamptz,
  last_used_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (tenant_id, key_prefix)
);

create table if not exists public.raw_operational_event_intake (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  ingestion_api_key_id uuid not null references public.ingestion_api_keys (id) on delete restrict,
  agent_installation_id uuid references public.agent_installations (id) on delete set null,
  workstation_id uuid references public.workstations (id) on delete set null,
  request_id uuid not null,
  batch_id text,
  source_event_id uuid not null,
  schema_version text not null,
  event_type text not null,
  occurred_at timestamptz not null,
  received_at timestamptz not null default timezone('utc', now()),
  payload_sha256 text not null,
  ingestion_status public.raw_intake_status not null default 'pending',
  duplicate_of_id uuid references public.raw_operational_event_intake (id) on delete set null,
  event_payload jsonb not null,
  request_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  unique (tenant_id, source_event_id)
);

create index if not exists idx_ingestion_api_keys_tenant_id on public.ingestion_api_keys (tenant_id, status);
create index if not exists idx_raw_operational_event_intake_tenant_received_at on public.raw_operational_event_intake (tenant_id, received_at desc);
create index if not exists idx_raw_operational_event_intake_status on public.raw_operational_event_intake (ingestion_status, received_at);
create index if not exists idx_raw_operational_event_intake_request_id on public.raw_operational_event_intake (request_id);
create index if not exists idx_raw_operational_event_intake_workstation on public.raw_operational_event_intake (tenant_id, workstation_id, occurred_at desc);

grant select, insert, update, delete on public.ingestion_api_keys to authenticated;
grant all privileges on public.ingestion_api_keys to service_role;
grant all privileges on public.raw_operational_event_intake to service_role;

alter table public.ingestion_api_keys enable row level security;
alter table public.raw_operational_event_intake enable row level security;

drop policy if exists ingestion_api_keys_read_admin on public.ingestion_api_keys;
create policy ingestion_api_keys_read_admin
on public.ingestion_api_keys
for select
to authenticated
using (public.can_manage_tenant(tenant_id));

drop policy if exists ingestion_api_keys_manage_admin on public.ingestion_api_keys;
create policy ingestion_api_keys_manage_admin
on public.ingestion_api_keys
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

drop trigger if exists trg_ingestion_api_keys_set_audit_fields on public.ingestion_api_keys;
create trigger trg_ingestion_api_keys_set_audit_fields
before insert or update on public.ingestion_api_keys
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_raw_operational_event_intake_set_audit_fields on public.raw_operational_event_intake;
create trigger trg_raw_operational_event_intake_set_audit_fields
before insert or update on public.raw_operational_event_intake
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_ingestion_api_keys_audit on public.ingestion_api_keys;
create trigger trg_ingestion_api_keys_audit
after insert or update or delete on public.ingestion_api_keys
for each row execute function app_private.write_audit_log();

