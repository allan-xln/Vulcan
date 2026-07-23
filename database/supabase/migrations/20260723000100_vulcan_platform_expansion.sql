-- Vulcan platform expansion foundation.
-- Additive by design: existing Workforce, agent and operational event flows remain valid.

create extension if not exists pgcrypto;

create or replace function app_private.vulcan_set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.tenant_modules (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  module_key text not null check (
    module_key in (
      'workforce',
      'infrastructure',
      'timeline',
      'assets',
      'print',
      'security',
      'intelligence',
      'automations',
      'compliance',
      'administration'
    )
  ),
  enabled boolean not null default false,
  plan_source text not null default 'tenant' check (plan_source in ('system', 'plan', 'tenant', 'trial')),
  limits jsonb not null default '{}'::jsonb,
  enabled_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, module_key)
);

create table if not exists public.sites (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  code text not null,
  name text not null,
  description text,
  address jsonb not null default '{}'::jsonb,
  timezone text not null default 'America/Sao_Paulo',
  status text not null default 'active' check (status in ('active', 'maintenance', 'inactive')),
  tags text[] not null default '{}'::text[],
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, code)
);

create table if not exists public.infrastructure_networks (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  site_id uuid not null,
  name text not null,
  description text,
  network_cidr cidr not null,
  gateway inet,
  vlan_id integer check (vlan_id is null or vlan_id between 1 and 4094),
  dns_servers inet[] not null default '{}'::inet[],
  dhcp_enabled boolean not null default false,
  discovery_allowed boolean not null default false,
  status text not null default 'active' check (status in ('active', 'maintenance', 'inactive')),
  tags text[] not null default '{}'::text[],
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, site_id, network_cidr),
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete cascade,
  check (gateway is null or gateway << network_cidr)
);

create table if not exists public.credential_references (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  name text not null,
  provider text not null,
  external_ref text not null,
  status text not null default 'untested' check (status in ('untested', 'valid', 'invalid', 'revoked')),
  last_tested_at timestamptz,
  last_test_result text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, provider, external_ref)
);

create table if not exists public.infrastructure_assets (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  site_id uuid,
  network_id uuid,
  parent_asset_id uuid,
  owner_membership_id uuid,
  department_id uuid,
  endpoint_device_id uuid,
  asset_type text not null check (
    asset_type in (
      'workstation',
      'server',
      'switch',
      'access_point',
      'firewall',
      'printer',
      'ups',
      'controller',
      'gateway',
      'service',
      'application',
      'storage',
      'virtual_machine',
      'container',
      'other'
    )
  ),
  name text not null,
  hostname text,
  description text,
  manufacturer text,
  model text,
  serial_number text,
  asset_tag text,
  ip_address inet,
  mac_address text,
  operating_system text,
  status text not null default 'unknown' check (status in ('online', 'degraded', 'offline', 'unknown', 'maintenance', 'retired')),
  criticality text not null default 'medium' check (criticality in ('low', 'medium', 'high', 'critical')),
  lifecycle_state text not null default 'managed' check (
    lifecycle_state in ('discovered', 'identified', 'pending_review', 'approved', 'ignored', 'blocked', 'managed', 'retired')
  ),
  responsible text,
  physical_location text,
  rack text,
  rack_position text,
  warranty_expires_at date,
  maintenance_window jsonb not null default '{}'::jsonb,
  documentation_url text,
  notes text,
  tags text[] not null default '{}'::text[],
  source text not null default 'manual',
  confidence numeric(5, 4) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  discovered_at timestamptz,
  last_seen_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete set null,
  foreign key (tenant_id, network_id) references public.infrastructure_networks (tenant_id, id) on delete set null,
  foreign key (tenant_id, parent_asset_id) references public.infrastructure_assets (tenant_id, id) on delete set null,
  foreign key (owner_membership_id) references public.memberships (id) on delete set null,
  foreign key (department_id) references public.departments (id) on delete set null,
  foreign key (endpoint_device_id) references public.devices (id) on delete set null,
  check (mac_address is null or mac_address ~* '^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$'),
  check (parent_asset_id is null or parent_asset_id <> id)
);

create unique index if not exists idx_infrastructure_assets_tenant_serial
  on public.infrastructure_assets (tenant_id, lower(serial_number))
  where serial_number is not null and btrim(serial_number) <> '';

create unique index if not exists idx_infrastructure_assets_tenant_asset_tag
  on public.infrastructure_assets (tenant_id, lower(asset_tag))
  where asset_tag is not null and btrim(asset_tag) <> '';

create table if not exists public.asset_interfaces (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  asset_id uuid not null,
  network_id uuid,
  name text not null,
  description text,
  if_index integer,
  interface_type text,
  mac_address text,
  ip_addresses inet[] not null default '{}'::inet[],
  vlan_id integer check (vlan_id is null or vlan_id between 1 and 4094),
  native_vlan_id integer check (native_vlan_id is null or native_vlan_id between 1 and 4094),
  administrative_status text not null default 'unknown' check (administrative_status in ('up', 'down', 'unknown')),
  operational_status text not null default 'unknown' check (operational_status in ('up', 'down', 'degraded', 'unknown')),
  speed_bps bigint check (speed_bps is null or speed_bps >= 0),
  duplex text check (duplex is null or duplex in ('half', 'full', 'auto', 'unknown')),
  poe_enabled boolean,
  counters jsonb not null default '{}'::jsonb,
  last_seen_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, asset_id, name),
  foreign key (tenant_id, asset_id) references public.infrastructure_assets (tenant_id, id) on delete cascade,
  foreign key (tenant_id, network_id) references public.infrastructure_networks (tenant_id, id) on delete set null,
  check (mac_address is null or mac_address ~* '^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$')
);

create table if not exists public.asset_relationships (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  source_asset_id uuid not null,
  target_asset_id uuid not null,
  source_interface_id uuid,
  target_interface_id uuid,
  relationship_type text not null check (
    relationship_type in ('connected_to', 'uplink', 'depends_on', 'hosts', 'runs', 'prints_through', 'powered_by', 'managed_by')
  ),
  source text not null default 'manual',
  confidence numeric(5, 4) not null default 1 check (confidence >= 0 and confidence <= 1),
  status text not null default 'active' check (status in ('active', 'stale', 'removed')),
  observed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, source_asset_id, target_asset_id, relationship_type),
  foreign key (tenant_id, source_asset_id) references public.infrastructure_assets (tenant_id, id) on delete cascade,
  foreign key (tenant_id, target_asset_id) references public.infrastructure_assets (tenant_id, id) on delete cascade,
  foreign key (tenant_id, source_interface_id) references public.asset_interfaces (tenant_id, id) on delete set null,
  foreign key (tenant_id, target_interface_id) references public.asset_interfaces (tenant_id, id) on delete set null,
  check (source_asset_id <> target_asset_id)
);

create table if not exists public.integration_instances (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  site_id uuid,
  credential_reference_id uuid,
  adapter_type text not null,
  name text not null,
  enabled boolean not null default false,
  read_only boolean not null default true check (read_only),
  status text not null default 'unconfigured' check (status in ('unconfigured', 'ready', 'degraded', 'failed', 'disabled')),
  capabilities text[] not null default '{}'::text[],
  sanitized_config jsonb not null default '{}'::jsonb,
  last_tested_at timestamptz,
  last_success_at timestamptz,
  last_error text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, adapter_type, name),
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete set null,
  foreign key (tenant_id, credential_reference_id) references public.credential_references (tenant_id, id) on delete set null,
  check (
    not (
      sanitized_config ?| array[
        'password',
        'secret',
        'token',
        'apiKey',
        'api_key',
        'community',
        'privateKey',
        'private_key'
      ]
    )
  )
);

create table if not exists public.discovery_policies (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  site_id uuid not null,
  name text not null,
  enabled boolean not null default false,
  read_only boolean not null default true check (read_only),
  safe_mode boolean not null default true check (safe_mode),
  allowed_networks cidr[] not null,
  denied_networks cidr[] not null default '{}'::cidr[],
  excluded_addresses inet[] not null default '{}'::inet[],
  allowed_protocols text[] not null default array['icmp', 'dns']::text[],
  allowed_tcp_ports integer[] not null default '{}'::integer[],
  frequency_minutes integer not null default 60 check (frequency_minutes between 5 and 10080),
  concurrency integer not null default 8 check (concurrency between 1 and 32),
  timeout_ms integer not null default 750 check (timeout_ms between 100 and 10000),
  max_targets integer not null default 256 check (max_targets between 1 and 4096),
  execution_window jsonb not null default '{}'::jsonb,
  last_run_at timestamptz,
  next_run_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, site_id, name),
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete cascade,
  check (cardinality(allowed_networks) > 0),
  check (allowed_protocols <@ array['icmp', 'dns', 'reverse_dns', 'arp', 'tcp_connect', 'snmp', 'lldp', 'cdp']::text[]),
  check (0 < all(allowed_tcp_ports) and 65536 > all(allowed_tcp_ports))
);

create table if not exists public.discovery_runs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  site_id uuid not null,
  policy_id uuid not null,
  requested_by uuid,
  status text not null default 'queued' check (status in ('queued', 'running', 'completed', 'partial', 'failed', 'cancelled')),
  mode text not null default 'read_only' check (mode = 'read_only'),
  started_at timestamptz,
  finished_at timestamptz,
  targets_planned integer not null default 0 check (targets_planned >= 0),
  targets_scanned integer not null default 0 check (targets_scanned >= 0),
  findings_count integer not null default 0 check (findings_count >= 0),
  error_count integer not null default 0 check (error_count >= 0),
  error_summary text,
  result_summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete cascade,
  foreign key (tenant_id, policy_id) references public.discovery_policies (tenant_id, id) on delete cascade,
  foreign key (requested_by) references auth.users (id) on delete set null,
  check (finished_at is null or started_at is null or finished_at >= started_at)
);

create table if not exists public.discovery_findings (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  run_id uuid not null,
  site_id uuid not null,
  matched_asset_id uuid,
  ip_address inet not null,
  mac_address text,
  hostname text,
  manufacturer text,
  probable_type text,
  confidence numeric(5, 4) not null default 0 check (confidence >= 0 and confidence <= 1),
  latency_ms numeric,
  packet_loss numeric check (packet_loss is null or (packet_loss >= 0 and packet_loss <= 1)),
  open_ports integer[] not null default '{}'::integer[],
  state text not null default 'discovered' check (
    state in ('discovered', 'identified', 'pending_review', 'approved', 'ignored', 'blocked', 'managed')
  ),
  observed_at timestamptz not null default timezone('utc', now()),
  raw_observation jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, run_id, ip_address),
  foreign key (tenant_id, run_id) references public.discovery_runs (tenant_id, id) on delete cascade,
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete cascade,
  foreign key (tenant_id, matched_asset_id) references public.infrastructure_assets (tenant_id, id) on delete set null,
  check (mac_address is null or mac_address ~* '^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$')
);

create table if not exists public.unified_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  schema_version text not null default '2026-07-vulcan-event.v1',
  site_id uuid,
  asset_id uuid,
  agent_id uuid,
  source text not null,
  source_type text not null,
  source_event_id text not null,
  event_type text not null,
  category text not null,
  severity text not null default 'info' check (severity in ('debug', 'info', 'notice', 'warning', 'error', 'critical')),
  occurred_at timestamptz not null,
  device_occurred_at timestamptz,
  received_at timestamptz not null default timezone('utc', now()),
  clock_drift_ms bigint,
  offline_buffered boolean not null default false,
  actor jsonb not null default '{}'::jsonb,
  device jsonb not null default '{}'::jsonb,
  context jsonb not null default '{}'::jsonb,
  metrics jsonb not null default '{}'::jsonb,
  message text not null,
  technical_message text,
  fingerprint text not null,
  correlation_id text,
  causation_id text,
  confidence numeric(5, 4) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  privacy_classification text not null default 'operational' check (
    privacy_classification in ('public', 'operational', 'personal', 'sensitive', 'restricted')
  ),
  retention_policy text not null default 'standard',
  trusted_origin boolean not null default false,
  data_origin text not null default 'real' check (data_origin in ('real', 'simulated', 'imported')),
  extensions jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, source, source_event_id),
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete set null,
  foreign key (tenant_id, asset_id) references public.infrastructure_assets (tenant_id, id) on delete set null,
  check (received_at >= '2000-01-01'::timestamptz),
  check (occurred_at >= '2000-01-01'::timestamptz)
);

create table if not exists public.incidents (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  site_id uuid,
  title text not null,
  summary text not null,
  impact text not null,
  severity text not null default 'warning' check (severity in ('info', 'notice', 'warning', 'error', 'critical')),
  status text not null default 'open' check (status in ('open', 'investigating', 'monitoring', 'resolved', 'closed')),
  probable_cause text,
  confidence numeric(5, 4) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  recommendation text,
  affected_entities jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '[]'::jsonb,
  first_occurred_at timestamptz not null,
  last_occurred_at timestamptz not null,
  assigned_membership_id uuid,
  resolution text,
  resolved_at timestamptz,
  fingerprint text not null,
  source text not null default 'rules',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, fingerprint),
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete set null,
  foreign key (assigned_membership_id) references public.memberships (id) on delete set null,
  check (last_occurred_at >= first_occurred_at)
);

create table if not exists public.incident_events (
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  incident_id uuid not null references public.incidents (id) on delete cascade,
  event_id uuid not null references public.unified_events (id) on delete cascade,
  relationship text not null default 'related' check (relationship in ('trigger', 'cause', 'impact', 'evidence', 'related')),
  created_at timestamptz not null default timezone('utc', now()),
  primary key (tenant_id, incident_id, event_id)
);

create table if not exists public.retention_policies (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  data_class text not null check (
    data_class in ('operational_events', 'metrics', 'logs', 'audit', 'prints', 'evidence', 'alerts', 'incidents', 'inventory', 'presence')
  ),
  retention_days integer not null check (retention_days between 1 and 3650),
  archive_after_days integer check (archive_after_days is null or archive_after_days between 1 and 3650),
  enabled boolean not null default true,
  legal_hold boolean not null default false,
  policy_version integer not null default 1 check (policy_version > 0),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, data_class)
);

create index if not exists idx_tenant_modules_tenant_enabled on public.tenant_modules (tenant_id, enabled);
create index if not exists idx_sites_tenant_status on public.sites (tenant_id, status, name);
create index if not exists idx_infrastructure_networks_site on public.infrastructure_networks (tenant_id, site_id, status);
create index if not exists idx_infrastructure_networks_cidr on public.infrastructure_networks using gist (network_cidr inet_ops);
create index if not exists idx_infrastructure_assets_tenant_status on public.infrastructure_assets (tenant_id, status, asset_type);
create index if not exists idx_infrastructure_assets_site on public.infrastructure_assets (tenant_id, site_id, status);
create index if not exists idx_infrastructure_assets_network on public.infrastructure_assets (tenant_id, network_id);
create index if not exists idx_infrastructure_assets_ip on public.infrastructure_assets (tenant_id, ip_address);
create index if not exists idx_infrastructure_assets_tags on public.infrastructure_assets using gin (tags);
create index if not exists idx_asset_interfaces_asset on public.asset_interfaces (tenant_id, asset_id, operational_status);
create index if not exists idx_asset_relationships_source on public.asset_relationships (tenant_id, source_asset_id, status);
create index if not exists idx_asset_relationships_target on public.asset_relationships (tenant_id, target_asset_id, status);
create index if not exists idx_integration_instances_tenant on public.integration_instances (tenant_id, adapter_type, status);
create index if not exists idx_discovery_policies_site on public.discovery_policies (tenant_id, site_id, enabled);
create index if not exists idx_discovery_runs_queue on public.discovery_runs (status, created_at) where status = 'queued';
create index if not exists idx_discovery_runs_tenant on public.discovery_runs (tenant_id, created_at desc);
create index if not exists idx_discovery_findings_run on public.discovery_findings (tenant_id, run_id, state);
create index if not exists idx_discovery_findings_ip on public.discovery_findings (tenant_id, ip_address, observed_at desc);
create index if not exists idx_unified_events_timeline on public.unified_events (tenant_id, occurred_at desc, id desc);
create index if not exists idx_unified_events_asset on public.unified_events (tenant_id, asset_id, occurred_at desc) where asset_id is not null;
create index if not exists idx_unified_events_site on public.unified_events (tenant_id, site_id, occurred_at desc) where site_id is not null;
create index if not exists idx_unified_events_agent on public.unified_events (tenant_id, agent_id, occurred_at desc) where agent_id is not null;
create index if not exists idx_unified_events_type on public.unified_events (tenant_id, event_type, occurred_at desc);
create index if not exists idx_unified_events_correlation on public.unified_events (tenant_id, correlation_id) where correlation_id is not null;
create index if not exists idx_unified_events_context on public.unified_events using gin (context);
create index if not exists idx_incidents_tenant_status on public.incidents (tenant_id, status, severity, last_occurred_at desc);
create index if not exists idx_incident_events_event on public.incident_events (tenant_id, event_id);

drop trigger if exists trg_tenant_modules_updated_at on public.tenant_modules;
create trigger trg_tenant_modules_updated_at before update on public.tenant_modules
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_sites_updated_at on public.sites;
create trigger trg_sites_updated_at before update on public.sites
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_infrastructure_networks_updated_at on public.infrastructure_networks;
create trigger trg_infrastructure_networks_updated_at before update on public.infrastructure_networks
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_credential_references_updated_at on public.credential_references;
create trigger trg_credential_references_updated_at before update on public.credential_references
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_infrastructure_assets_updated_at on public.infrastructure_assets;
create trigger trg_infrastructure_assets_updated_at before update on public.infrastructure_assets
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_asset_interfaces_updated_at on public.asset_interfaces;
create trigger trg_asset_interfaces_updated_at before update on public.asset_interfaces
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_asset_relationships_updated_at on public.asset_relationships;
create trigger trg_asset_relationships_updated_at before update on public.asset_relationships
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_integration_instances_updated_at on public.integration_instances;
create trigger trg_integration_instances_updated_at before update on public.integration_instances
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_discovery_policies_updated_at on public.discovery_policies;
create trigger trg_discovery_policies_updated_at before update on public.discovery_policies
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_discovery_runs_updated_at on public.discovery_runs;
create trigger trg_discovery_runs_updated_at before update on public.discovery_runs
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_discovery_findings_updated_at on public.discovery_findings;
create trigger trg_discovery_findings_updated_at before update on public.discovery_findings
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_incidents_updated_at on public.incidents;
create trigger trg_incidents_updated_at before update on public.incidents
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_retention_policies_updated_at on public.retention_policies;
create trigger trg_retention_policies_updated_at before update on public.retention_policies
for each row execute function app_private.vulcan_set_updated_at();

alter table public.tenant_modules enable row level security;
alter table public.sites enable row level security;
alter table public.infrastructure_networks enable row level security;
alter table public.credential_references enable row level security;
alter table public.infrastructure_assets enable row level security;
alter table public.asset_interfaces enable row level security;
alter table public.asset_relationships enable row level security;
alter table public.integration_instances enable row level security;
alter table public.discovery_policies enable row level security;
alter table public.discovery_runs enable row level security;
alter table public.discovery_findings enable row level security;
alter table public.unified_events enable row level security;
alter table public.incidents enable row level security;
alter table public.incident_events enable row level security;
alter table public.retention_policies enable row level security;

drop policy if exists tenant_modules_read_member on public.tenant_modules;
create policy tenant_modules_read_member on public.tenant_modules
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists tenant_modules_manage_admin on public.tenant_modules;
create policy tenant_modules_manage_admin on public.tenant_modules
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists sites_read_member on public.sites;
create policy sites_read_member on public.sites
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists sites_manage_admin on public.sites;
create policy sites_manage_admin on public.sites
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists infrastructure_networks_read_member on public.infrastructure_networks;
create policy infrastructure_networks_read_member on public.infrastructure_networks
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists infrastructure_networks_manage_admin on public.infrastructure_networks;
create policy infrastructure_networks_manage_admin on public.infrastructure_networks
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists credential_references_read_admin on public.credential_references;
create policy credential_references_read_admin on public.credential_references
for select to authenticated using (public.vulcan_has_tenant_scope(tenant_id));
drop policy if exists credential_references_manage_admin on public.credential_references;
create policy credential_references_manage_admin on public.credential_references
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists infrastructure_assets_read_member on public.infrastructure_assets;
create policy infrastructure_assets_read_member on public.infrastructure_assets
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists infrastructure_assets_manage_admin on public.infrastructure_assets;
create policy infrastructure_assets_manage_admin on public.infrastructure_assets
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists asset_interfaces_read_member on public.asset_interfaces;
create policy asset_interfaces_read_member on public.asset_interfaces
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists asset_interfaces_manage_admin on public.asset_interfaces;
create policy asset_interfaces_manage_admin on public.asset_interfaces
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists asset_relationships_read_member on public.asset_relationships;
create policy asset_relationships_read_member on public.asset_relationships
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists asset_relationships_manage_admin on public.asset_relationships;
create policy asset_relationships_manage_admin on public.asset_relationships
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists integration_instances_read_admin on public.integration_instances;
create policy integration_instances_read_admin on public.integration_instances
for select to authenticated using (public.vulcan_has_tenant_scope(tenant_id));
drop policy if exists integration_instances_manage_admin on public.integration_instances;
create policy integration_instances_manage_admin on public.integration_instances
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists discovery_policies_read_member on public.discovery_policies;
create policy discovery_policies_read_member on public.discovery_policies
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists discovery_policies_manage_admin on public.discovery_policies;
create policy discovery_policies_manage_admin on public.discovery_policies
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists discovery_runs_read_member on public.discovery_runs;
create policy discovery_runs_read_member on public.discovery_runs
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists discovery_runs_manage_admin on public.discovery_runs;
create policy discovery_runs_manage_admin on public.discovery_runs
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists discovery_findings_read_member on public.discovery_findings;
create policy discovery_findings_read_member on public.discovery_findings
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists discovery_findings_manage_admin on public.discovery_findings;
create policy discovery_findings_manage_admin on public.discovery_findings
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists unified_events_read_member on public.unified_events;
create policy unified_events_read_member on public.unified_events
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));

drop policy if exists incidents_read_member on public.incidents;
create policy incidents_read_member on public.incidents
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists incidents_manage_admin on public.incidents;
create policy incidents_manage_admin on public.incidents
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists incident_events_read_member on public.incident_events;
create policy incident_events_read_member on public.incident_events
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists incident_events_manage_admin on public.incident_events;
create policy incident_events_manage_admin on public.incident_events
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists retention_policies_read_member on public.retention_policies;
create policy retention_policies_read_member on public.retention_policies
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists retention_policies_manage_admin on public.retention_policies;
create policy retention_policies_manage_admin on public.retention_policies
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists service_role_all_tenant_modules on public.tenant_modules;
create policy service_role_all_tenant_modules on public.tenant_modules
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_sites on public.sites;
create policy service_role_all_sites on public.sites
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_infrastructure_networks on public.infrastructure_networks;
create policy service_role_all_infrastructure_networks on public.infrastructure_networks
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_credential_references on public.credential_references;
create policy service_role_all_credential_references on public.credential_references
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_infrastructure_assets on public.infrastructure_assets;
create policy service_role_all_infrastructure_assets on public.infrastructure_assets
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_asset_interfaces on public.asset_interfaces;
create policy service_role_all_asset_interfaces on public.asset_interfaces
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_asset_relationships on public.asset_relationships;
create policy service_role_all_asset_relationships on public.asset_relationships
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_integration_instances on public.integration_instances;
create policy service_role_all_integration_instances on public.integration_instances
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_discovery_policies on public.discovery_policies;
create policy service_role_all_discovery_policies on public.discovery_policies
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_discovery_runs on public.discovery_runs;
create policy service_role_all_discovery_runs on public.discovery_runs
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_discovery_findings on public.discovery_findings;
create policy service_role_all_discovery_findings on public.discovery_findings
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_unified_events on public.unified_events;
create policy service_role_all_unified_events on public.unified_events
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_incidents on public.incidents;
create policy service_role_all_incidents on public.incidents
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_incident_events on public.incident_events;
create policy service_role_all_incident_events on public.incident_events
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_retention_policies on public.retention_policies;
create policy service_role_all_retention_policies on public.retention_policies
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant select on public.tenant_modules, public.sites, public.infrastructure_networks,
  public.infrastructure_assets, public.asset_interfaces, public.asset_relationships,
  public.discovery_policies, public.discovery_runs, public.discovery_findings,
  public.unified_events, public.incidents, public.incident_events, public.retention_policies
to authenticated;
grant select, insert, update, delete on public.credential_references, public.integration_instances
to authenticated;
grant insert, update, delete on public.tenant_modules, public.sites, public.infrastructure_networks,
  public.infrastructure_assets, public.asset_interfaces, public.asset_relationships,
  public.discovery_policies, public.discovery_runs, public.discovery_findings,
  public.incidents, public.incident_events, public.retention_policies
to authenticated;
grant all privileges on public.tenant_modules, public.sites, public.infrastructure_networks,
  public.credential_references, public.infrastructure_assets, public.asset_interfaces,
  public.asset_relationships, public.integration_instances, public.discovery_policies,
  public.discovery_runs, public.discovery_findings, public.unified_events, public.incidents,
  public.incident_events, public.retention_policies
to service_role;

insert into public.tenant_modules (tenant_id, module_key, enabled, plan_source, enabled_at)
select
  tenant.id,
  module.module_key,
  module.module_key in ('workforce', 'infrastructure', 'timeline', 'assets'),
  case when module.module_key = 'workforce' then 'system' else 'tenant' end,
  case when module.module_key in ('workforce', 'infrastructure', 'timeline', 'assets')
    then timezone('utc', now())
    else null
  end
from public.tenants tenant
cross join (
  values
    ('workforce'),
    ('infrastructure'),
    ('timeline'),
    ('assets'),
    ('print'),
    ('security'),
    ('intelligence'),
    ('automations'),
    ('compliance'),
    ('administration')
) as module(module_key)
on conflict (tenant_id, module_key) do nothing;

insert into public.retention_policies (tenant_id, data_class, retention_days)
select tenant.id, policy.data_class, policy.retention_days
from public.tenants tenant
cross join (
  values
    ('operational_events', 90),
    ('metrics', 365),
    ('logs', 30),
    ('audit', 365),
    ('prints', 90),
    ('evidence', 180),
    ('alerts', 180),
    ('incidents', 730),
    ('inventory', 730),
    ('presence', 90)
) as policy(data_class, retention_days)
on conflict (tenant_id, data_class) do nothing;

insert into public.permissions (permission_key, name, description, resource, action)
values
  ('infrastructure.read', 'Visualizar infraestrutura', 'Visualiza sites, redes e ativos permitidos.', 'infrastructure', 'read'),
  ('infrastructure.manage', 'Gerenciar infraestrutura', 'Cadastra e altera sites, redes e ativos.', 'infrastructure', 'manage'),
  ('timeline.read', 'Visualizar timeline', 'Visualiza eventos unificados do escopo permitido.', 'timeline', 'read'),
  ('timeline.export', 'Exportar timeline', 'Exporta eventos unificados auditados.', 'timeline', 'export'),
  ('discovery.read', 'Visualizar discovery', 'Visualiza políticas, execuções e descobertas.', 'discovery', 'read'),
  ('discovery.execute', 'Executar discovery', 'Solicita discovery somente leitura em redes permitidas.', 'discovery', 'execute'),
  ('discovery.approve', 'Aprovar descoberta', 'Aprova ou ignora ativos descobertos.', 'discovery', 'approve'),
  ('integrations.manage', 'Gerenciar integrações', 'Gerencia adapters e referências de credencial.', 'integrations', 'manage'),
  ('incidents.read', 'Visualizar incidentes', 'Visualiza incidentes e evidências.', 'incidents', 'read'),
  ('incidents.manage', 'Gerenciar incidentes', 'Atualiza responsável, status e resolução.', 'incidents', 'manage'),
  ('platform.health.read', 'Visualizar saúde da plataforma', 'Visualiza saúde técnica sem expor segredos.', 'platform_health', 'read')
on conflict (permission_key) do nothing;

insert into public.roles (tenant_id, slug, name, description, is_system, scope)
select tenant.id, role.slug, role.name, role.description, true, role.scope
from public.tenants tenant
cross join (
  values
    ('tenant_owner', 'Proprietário do tenant', 'Controle comercial e administrativo do tenant.', 'tenant'),
    ('tenant_admin', 'Administrador do tenant', 'Administração operacional do tenant.', 'tenant'),
    ('infrastructure_admin', 'Administrador de infraestrutura', 'Administração de ativos, discovery e integrações.', 'tenant'),
    ('security_admin', 'Administrador de segurança', 'Administração dos módulos de segurança.', 'tenant'),
    ('manager', 'Gerente', 'Gestão da própria hierarquia.', 'hierarchy'),
    ('supervisor', 'Supervisor', 'Supervisão da própria subárvore.', 'hierarchy'),
    ('auditor', 'Auditor', 'Leitura auditável do tenant.', 'tenant'),
    ('analyst', 'Analista', 'Análise operacional no escopo permitido.', 'hierarchy'),
    ('employee', 'Colaborador', 'Acesso aos próprios dados operacionais.', 'self'),
    ('read_only', 'Somente leitura', 'Leitura sem mutação no escopo permitido.', 'tenant')
) as role(slug, name, description, scope)
on conflict (tenant_id, slug) do nothing;

insert into public.role_permissions (role_id, permission_id)
select role.id, permission.id
from public.roles role
join public.permissions permission on (
  role.slug in ('admin', 'tenant_owner', 'tenant_admin', 'infrastructure_admin')
  and permission.permission_key in (
    'infrastructure.read',
    'infrastructure.manage',
    'timeline.read',
    'timeline.export',
    'discovery.read',
    'discovery.execute',
    'discovery.approve',
    'integrations.manage',
    'incidents.read',
    'incidents.manage',
    'platform.health.read'
  )
) or (
  role.slug in ('manager', 'supervisor', 'auditor', 'analyst', 'read_only')
  and permission.permission_key in ('infrastructure.read', 'timeline.read', 'discovery.read', 'incidents.read')
)
on conflict (role_id, permission_id) do nothing;

create or replace function app_private.vulcan_initialize_tenant_platform()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.tenant_modules (tenant_id, module_key, enabled, plan_source, enabled_at)
  select
    new.id,
    module.module_key,
    module.module_key in ('workforce', 'infrastructure', 'timeline', 'assets'),
    case when module.module_key = 'workforce' then 'system' else 'tenant' end,
    case when module.module_key in ('workforce', 'infrastructure', 'timeline', 'assets')
      then timezone('utc', now())
      else null
    end
  from (
    values
      ('workforce'),
      ('infrastructure'),
      ('timeline'),
      ('assets'),
      ('print'),
      ('security'),
      ('intelligence'),
      ('automations'),
      ('compliance'),
      ('administration')
  ) as module(module_key)
  on conflict (tenant_id, module_key) do nothing;

  insert into public.retention_policies (tenant_id, data_class, retention_days)
  select new.id, policy.data_class, policy.retention_days
  from (
    values
      ('operational_events', 90),
      ('metrics', 365),
      ('logs', 30),
      ('audit', 365),
      ('prints', 90),
      ('evidence', 180),
      ('alerts', 180),
      ('incidents', 730),
      ('inventory', 730),
      ('presence', 90)
  ) as policy(data_class, retention_days)
  on conflict (tenant_id, data_class) do nothing;

  insert into public.roles (tenant_id, slug, name, description, is_system, scope)
  select new.id, role.slug, role.name, role.description, true, role.scope
  from (
    values
      ('tenant_owner', 'Proprietário do tenant', 'Controle comercial e administrativo do tenant.', 'tenant'),
      ('tenant_admin', 'Administrador do tenant', 'Administração operacional do tenant.', 'tenant'),
      ('infrastructure_admin', 'Administrador de infraestrutura', 'Administração de ativos, discovery e integrações.', 'tenant'),
      ('security_admin', 'Administrador de segurança', 'Administração dos módulos de segurança.', 'tenant'),
      ('manager', 'Gerente', 'Gestão da própria hierarquia.', 'hierarchy'),
      ('supervisor', 'Supervisor', 'Supervisão da própria subárvore.', 'hierarchy'),
      ('auditor', 'Auditor', 'Leitura auditável do tenant.', 'tenant'),
      ('analyst', 'Analista', 'Análise operacional no escopo permitido.', 'hierarchy'),
      ('employee', 'Colaborador', 'Acesso aos próprios dados operacionais.', 'self'),
      ('read_only', 'Somente leitura', 'Leitura sem mutação no escopo permitido.', 'tenant')
  ) as role(slug, name, description, scope)
  on conflict (tenant_id, slug) do nothing;

  insert into public.role_permissions (role_id, permission_id)
  select role.id, permission.id
  from public.roles role
  join public.permissions permission on (
    role.slug in ('admin', 'tenant_owner', 'tenant_admin', 'infrastructure_admin')
    and permission.permission_key in (
      'infrastructure.read',
      'infrastructure.manage',
      'timeline.read',
      'timeline.export',
      'discovery.read',
      'discovery.execute',
      'discovery.approve',
      'integrations.manage',
      'incidents.read',
      'incidents.manage',
      'platform.health.read'
    )
  ) or (
    role.slug in ('manager', 'supervisor', 'auditor', 'analyst', 'read_only')
    and permission.permission_key in ('infrastructure.read', 'timeline.read', 'discovery.read', 'incidents.read')
  )
  where role.tenant_id = new.id
  on conflict (role_id, permission_id) do nothing;

  return new;
end;
$$;

drop trigger if exists trg_tenants_initialize_platform on public.tenants;
create trigger trg_tenants_initialize_platform
after insert on public.tenants
for each row execute function app_private.vulcan_initialize_tenant_platform();

create or replace function app_private.vulcan_mirror_activity_event()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_source_event_id text;
  v_message text;
  v_severity text;
  v_data_origin text;
begin
  v_source_event_id := coalesce(nullif(new.source_event_id, ''), new.id::text);
  v_severity := case
    when new.event_type in ('agent_error', 'application_crash') then 'warning'
    else 'info'
  end;
  v_data_origin := case
    when coalesce(new.metadata ->> 'seed', '') = 'vulcan-demo' then 'simulated'
    else 'real'
  end;
  v_message := case
    when new.event_type in ('idle_started', 'idle_start') then 'O período de ociosidade foi iniciado.'
    when new.event_type in ('idle_ended', 'idle_end') then 'O período de ociosidade foi encerrado.'
    when new.event_type in ('user_logged_in', 'session_login') then 'O usuário iniciou uma sessão.'
    when new.event_type in ('user_logged_out', 'session_logout') then 'O usuário encerrou a sessão.'
    when new.event_type = 'context_switch' then 'O usuário alternou o contexto de trabalho.'
    when new.event_type = 'agent_error' then 'O agente encontrou um erro de coleta ou sincronização.'
    when new.app_name is not null then format('O aplicativo %s registrou atividade operacional.', new.app_name)
    else format('O evento operacional %s foi registrado.', new.event_type)
  end;

  insert into public.unified_events (
    id,
    tenant_id,
    schema_version,
    agent_id,
    source,
    source_type,
    source_event_id,
    event_type,
    category,
    severity,
    occurred_at,
    device_occurred_at,
    received_at,
    offline_buffered,
    actor,
    device,
    context,
    metrics,
    message,
    technical_message,
    fingerprint,
    privacy_classification,
    retention_policy,
    trusted_origin,
    data_origin,
    extensions
  )
  values (
    new.id,
    new.tenant_id,
    '2026-07-vulcan-event.v1',
    new.device_id,
    coalesce(nullif(new.metadata ->> 'source', ''), 'vulcan-agent'),
    'endpoint',
    v_source_event_id,
    new.event_type,
    coalesce(nullif(new.category, ''), 'workforce'),
    v_severity,
    new.occurred_at,
    new.occurred_at,
    new.created_at,
    lower(coalesce(new.metadata ->> 'offlineQueued', 'false')) in ('true', '1', 'yes'),
    jsonb_strip_nulls(jsonb_build_object('membershipId', new.membership_id)),
    jsonb_strip_nulls(jsonb_build_object('deviceId', new.device_id)),
    jsonb_strip_nulls(jsonb_build_object(
      'appName', new.app_name,
      'windowTitle', new.window_title,
      'activityEventId', new.id
    )) || new.metadata,
    jsonb_strip_nulls(jsonb_build_object('durationSeconds', new.duration_seconds)),
    v_message,
    format('%s%s', new.event_type, case when new.app_name is null then '' else ': ' || new.app_name end),
    encode(digest(concat_ws(':', new.tenant_id::text, new.event_type, coalesce(new.device_id::text, ''), v_source_event_id), 'sha256'), 'hex'),
    'operational',
    'standard',
    true,
    v_data_origin,
    jsonb_build_object('legacyActivityEvent', true)
  )
  on conflict (tenant_id, source, source_event_id) do nothing;

  return new;
end;
$$;

drop trigger if exists trg_activity_events_unified_mirror on public.activity_events;
create trigger trg_activity_events_unified_mirror
after insert on public.activity_events
for each row execute function app_private.vulcan_mirror_activity_event();

insert into public.unified_events (
  id,
  tenant_id,
  schema_version,
  agent_id,
  source,
  source_type,
  source_event_id,
  event_type,
  category,
  severity,
  occurred_at,
  device_occurred_at,
  received_at,
  offline_buffered,
  actor,
  device,
  context,
  metrics,
  message,
  technical_message,
  fingerprint,
  privacy_classification,
  retention_policy,
  trusted_origin,
  data_origin,
  extensions
)
select
  event.id,
  event.tenant_id,
  '2026-07-vulcan-event.v1',
  event.device_id,
  coalesce(nullif(event.metadata ->> 'source', ''), 'vulcan-agent'),
  'endpoint',
  coalesce(nullif(event.source_event_id, ''), event.id::text),
  event.event_type,
  coalesce(nullif(event.category, ''), 'workforce'),
  case when event.event_type in ('agent_error', 'application_crash') then 'warning' else 'info' end,
  event.occurred_at,
  event.occurred_at,
  event.created_at,
  lower(coalesce(event.metadata ->> 'offlineQueued', 'false')) in ('true', '1', 'yes'),
  jsonb_strip_nulls(jsonb_build_object('membershipId', event.membership_id)),
  jsonb_strip_nulls(jsonb_build_object('deviceId', event.device_id)),
  jsonb_strip_nulls(jsonb_build_object(
    'appName', event.app_name,
    'windowTitle', event.window_title,
    'activityEventId', event.id
  )) || event.metadata,
  jsonb_strip_nulls(jsonb_build_object('durationSeconds', event.duration_seconds)),
  case
    when event.event_type in ('idle_started', 'idle_start') then 'O período de ociosidade foi iniciado.'
    when event.event_type in ('idle_ended', 'idle_end') then 'O período de ociosidade foi encerrado.'
    when event.event_type in ('user_logged_in', 'session_login') then 'O usuário iniciou uma sessão.'
    when event.event_type in ('user_logged_out', 'session_logout') then 'O usuário encerrou a sessão.'
    when event.event_type = 'context_switch' then 'O usuário alternou o contexto de trabalho.'
    when event.event_type = 'agent_error' then 'O agente encontrou um erro de coleta ou sincronização.'
    when event.app_name is not null then format('O aplicativo %s registrou atividade operacional.', event.app_name)
    else format('O evento operacional %s foi registrado.', event.event_type)
  end,
  format('%s%s', event.event_type, case when event.app_name is null then '' else ': ' || event.app_name end),
  encode(digest(concat_ws(
    ':',
    event.tenant_id::text,
    event.event_type,
    coalesce(event.device_id::text, ''),
    coalesce(nullif(event.source_event_id, ''), event.id::text)
  ), 'sha256'), 'hex'),
  'operational',
  'standard',
  true,
  case when coalesce(event.metadata ->> 'seed', '') = 'vulcan-demo' then 'simulated' else 'real' end,
  jsonb_build_object('legacyActivityEvent', true, 'backfilled', true)
from public.activity_events event
on conflict (tenant_id, source, source_event_id) do nothing;

do $$
declare
  v_table text;
begin
  foreach v_table in array array[
    'tenant_modules',
    'sites',
    'infrastructure_networks',
    'credential_references',
    'infrastructure_assets',
    'asset_interfaces',
    'asset_relationships',
    'integration_instances',
    'discovery_policies',
    'discovery_runs',
    'incidents',
    'retention_policies'
  ]
  loop
    execute format('drop trigger if exists trg_%I_platform_audit on public.%I', v_table, v_table);
    execute format(
      'create trigger trg_%I_platform_audit after insert or update or delete on public.%I for each row execute function app_private.write_audit_log()',
      v_table,
      v_table
    );
  end loop;
end
$$;
