-- Vulcan Agent v2 security and policy foundation.
-- Additive migration: legacy agent routes and records remain valid during migration.

create extension if not exists pgcrypto;

create unique index if not exists uq_devices_tenant_id_id
  on public.devices (tenant_id, id);

create table if not exists public.agent_enrollment_tokens (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  token_prefix text not null,
  token_hash text not null unique,
  profile text not null default 'workstation'
    check (profile in ('workstation', 'server', 'collector')),
  site_id uuid,
  department_id uuid references public.departments (id) on delete set null,
  tags text[] not null default '{}'::text[],
  approval_mode text not null default 'automatic'
    check (approval_mode in ('automatic', 'manual')),
  expires_at timestamptz not null,
  max_uses integer not null default 1 check (max_uses between 1 and 10000),
  use_count integer not null default 0 check (use_count >= 0),
  last_used_at timestamptz,
  revoked_at timestamptz,
  created_by uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, token_prefix),
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete set null,
  check (expires_at > created_at),
  check (use_count <= max_uses)
);

create table if not exists public.agent_identities (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  device_id uuid not null,
  enrollment_token_id uuid,
  profile text not null check (profile in ('workstation', 'server', 'collector')),
  public_key text not null,
  public_key_fingerprint text not null unique,
  device_fingerprint text not null,
  hostname text not null,
  operating_system text not null,
  architecture text,
  agent_version text,
  status text not null default 'pending'
    check (status in ('pending', 'approved', 'online', 'offline', 'revoked', 'retired')),
  policy_revision bigint not null default 0 check (policy_revision >= 0),
  policy_status text not null default 'pending'
    check (policy_status in ('pending', 'applied', 'rejected', 'rollback')),
  queue_depth integer not null default 0 check (queue_depth >= 0),
  last_seen_at timestamptz,
  last_ip inet,
  revoked_at timestamptz,
  revocation_reason text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, device_fingerprint),
  foreign key (tenant_id, device_id) references public.devices (tenant_id, id) on delete cascade,
  foreign key (tenant_id, enrollment_token_id)
    references public.agent_enrollment_tokens (tenant_id, id) on delete set null
);

create table if not exists public.agent_policies (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  name text not null,
  profile text not null check (profile in ('workstation', 'server', 'collector')),
  scope_type text not null default 'tenant'
    check (scope_type in ('tenant', 'site', 'department', 'device')),
  site_id uuid,
  department_id uuid references public.departments (id) on delete cascade,
  device_id uuid,
  revision bigint not null default 1 check (revision > 0),
  schema_version text not null default 'v1',
  document jsonb not null,
  enabled boolean not null default true,
  created_by uuid references auth.users (id) on delete set null,
  updated_by uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique nulls not distinct (
    tenant_id,
    profile,
    scope_type,
    site_id,
    department_id,
    device_id,
    revision
  ),
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete cascade,
  foreign key (tenant_id, device_id) references public.devices (tenant_id, id) on delete cascade,
  check (
    (scope_type = 'tenant' and site_id is null and department_id is null and device_id is null)
    or (scope_type = 'site' and site_id is not null and department_id is null and device_id is null)
    or (scope_type = 'department' and site_id is null and department_id is not null and device_id is null)
    or (scope_type = 'device' and site_id is null and department_id is null and device_id is not null)
  )
);

create table if not exists public.agent_request_nonces (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  agent_identity_id uuid not null,
  nonce text not null,
  request_timestamp timestamptz not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default timezone('utc', now()),
  unique (agent_identity_id, nonce),
  foreign key (tenant_id, agent_identity_id)
    references public.agent_identities (tenant_id, id) on delete cascade,
  check (expires_at > request_timestamp)
);

create table if not exists public.agent_commands (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  agent_identity_id uuid not null,
  command_type text not null check (
    command_type in (
      'request_inventory',
      'request_diagnostics',
      'refresh_policy',
      'restart_agent',
      'rotate_credentials',
      'collect_logs',
      'run_health_check',
      'update_agent'
    )
  ),
  reason text not null,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'pending'
    check (status in ('pending', 'delivered', 'running', 'succeeded', 'failed', 'expired', 'cancelled')),
  requested_by uuid references auth.users (id) on delete set null,
  expires_at timestamptz not null,
  delivered_at timestamptz,
  completed_at timestamptz,
  output_summary text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  foreign key (tenant_id, agent_identity_id)
    references public.agent_identities (tenant_id, id) on delete cascade,
  check (expires_at > created_at),
  check (octet_length(payload::text) <= 65536),
  check (output_summary is null or octet_length(output_summary) <= 16384)
);

create table if not exists public.agent_releases (
  id uuid primary key default gen_random_uuid(),
  version text not null,
  channel text not null check (channel in ('stable', 'beta')),
  operating_system text not null check (operating_system in ('windows', 'linux')),
  architecture text not null check (architecture in ('amd64', 'arm64')),
  package_url text not null,
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  manifest_signature text not null,
  rollout_percent integer not null default 0 check (rollout_percent between 0 and 100),
  enabled boolean not null default false,
  minimum_version text,
  metadata jsonb not null default '{}'::jsonb,
  created_by uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (version, channel, operating_system, architecture)
);

create index if not exists idx_agent_enrollment_tokens_tenant_expiry
  on public.agent_enrollment_tokens (tenant_id, expires_at desc)
  where revoked_at is null;
create index if not exists idx_agent_identities_tenant_status
  on public.agent_identities (tenant_id, status, last_seen_at desc);
create index if not exists idx_agent_identities_device
  on public.agent_identities (tenant_id, device_id);
create index if not exists idx_agent_policies_resolution
  on public.agent_policies (tenant_id, profile, enabled, scope_type, revision desc);
create index if not exists idx_agent_request_nonces_expiry
  on public.agent_request_nonces (expires_at);
create index if not exists idx_agent_commands_delivery
  on public.agent_commands (agent_identity_id, status, created_at)
  where status = 'pending';

alter table public.agent_enrollment_tokens enable row level security;
alter table public.agent_identities enable row level security;
alter table public.agent_policies enable row level security;
alter table public.agent_request_nonces enable row level security;
alter table public.agent_commands enable row level security;
alter table public.agent_releases enable row level security;

drop policy if exists service_role_all_agent_enrollment_tokens on public.agent_enrollment_tokens;
create policy service_role_all_agent_enrollment_tokens on public.agent_enrollment_tokens
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_agent_identities on public.agent_identities;
create policy service_role_all_agent_identities on public.agent_identities
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_agent_policies on public.agent_policies;
create policy service_role_all_agent_policies on public.agent_policies
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_agent_request_nonces on public.agent_request_nonces;
create policy service_role_all_agent_request_nonces on public.agent_request_nonces
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_agent_commands on public.agent_commands;
create policy service_role_all_agent_commands on public.agent_commands
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_agent_releases on public.agent_releases;
create policy service_role_all_agent_releases on public.agent_releases
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant all privileges on public.agent_enrollment_tokens, public.agent_identities,
  public.agent_policies, public.agent_request_nonces, public.agent_commands,
  public.agent_releases
to service_role;

insert into public.permissions (permission_key, name, description, resource, action)
values
  ('agents.read', 'Visualizar agentes', 'Visualiza agentes do tenant e seus estados operacionais.', 'agents', 'read'),
  ('agents.manage', 'Gerenciar agentes', 'Cria enrollment, políticas e gerencia identidades de agentes.', 'agents', 'manage'),
  ('agents.commands', 'Solicitar comandos seguros', 'Solicita somente comandos tipados permitidos e auditados.', 'agents', 'commands'),
  ('agents.audit', 'Auditar agentes', 'Visualiza enrollment, políticas, comandos e eventos de auditoria.', 'agents', 'audit')
on conflict (permission_key) do nothing;

insert into public.role_permissions (role_id, permission_id)
select role.id, permission.id
from public.roles role
join public.permissions permission
  on permission.permission_key in ('agents.read', 'agents.manage', 'agents.commands', 'agents.audit')
where role.slug in ('owner', 'admin', 'tenant_owner', 'tenant_admin', 'infrastructure_admin', 'security_admin')
on conflict (role_id, permission_id) do nothing;

insert into public.role_permissions (role_id, permission_id)
select role.id, permission.id
from public.roles role
join public.permissions permission
  on permission.permission_key in ('agents.read', 'agents.audit')
where role.slug in ('manager', 'supervisor', 'auditor', 'analyst', 'read_only')
on conflict (role_id, permission_id) do nothing;

do $$
declare
  v_table text;
begin
  foreach v_table in array array[
    'agent_enrollment_tokens',
    'agent_identities',
    'agent_policies',
    'agent_commands',
    'agent_releases'
  ]
  loop
    execute format('drop trigger if exists trg_%I_set_updated_at on public.%I', v_table, v_table);
    execute format(
      'create trigger trg_%I_set_updated_at before update on public.%I for each row execute function app_private.vulcan_set_updated_at()',
      v_table,
      v_table
    );
    execute format('drop trigger if exists trg_%I_audit on public.%I', v_table, v_table);
    execute format(
      'create trigger trg_%I_audit after insert or update or delete on public.%I for each row execute function app_private.write_audit_log()',
      v_table,
      v_table
    );
  end loop;
end
$$;
