insert into public.subscription_plans (
  id,
  plan_key,
  name,
  description,
  billing_interval,
  price_cents,
  included_members,
  included_workstations,
  included_monthly_events,
  features
) values
  (
    '00000000-0000-0000-0000-000000000101',
    'starter',
    'Starter',
    'Starter plan for local development and small pilots.',
    'monthly',
    9900,
    25,
    50,
    500000,
    '{"ai_explanations": true, "hierarchical_analytics": true}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000102',
    'growth',
    'Growth',
    'Expanded plan for production-minded tenant testing.',
    'monthly',
    29900,
    100,
    250,
    5000000,
    '{"ai_explanations": true, "hierarchical_analytics": true, "priority_support": true}'::jsonb
  )
on conflict (id) do update
set
  name = excluded.name,
  description = excluded.description,
  price_cents = excluded.price_cents,
  included_members = excluded.included_members,
  included_workstations = excluded.included_workstations,
  included_monthly_events = excluded.included_monthly_events,
  features = excluded.features,
  updated_at = timezone('utc', now());

insert into public.permissions (
  id,
  permission_key,
  name,
  description,
  resource,
  action
) values
  ('00000000-0000-0000-0000-000000000201', 'tenant.manage', 'Manage tenant', 'Manage tenant settings and lifecycle.', 'tenant', 'manage'),
  ('00000000-0000-0000-0000-000000000202', 'membership.manage', 'Manage memberships', 'Invite and manage tenant memberships.', 'membership', 'manage'),
  ('00000000-0000-0000-0000-000000000203', 'org.manage', 'Manage hierarchy', 'Manage organizational nodes and edges.', 'organization', 'manage'),
  ('00000000-0000-0000-0000-000000000204', 'telemetry.manage', 'Manage telemetry', 'Manage telemetry policies and agent approvals.', 'telemetry', 'manage'),
  ('00000000-0000-0000-0000-000000000205', 'audit.read', 'Read audit logs', 'Read audit trails for tenant-scoped changes.', 'audit', 'read')
on conflict (permission_key) do update
set
  name = excluded.name,
  description = excluded.description,
  resource = excluded.resource,
  action = excluded.action,
  updated_at = timezone('utc', now());

insert into public.tenants (
  id,
  subscription_plan_id,
  slug,
  legal_name,
  display_name,
  billing_email,
  status,
  country_code,
  timezone,
  metadata
) values (
  '00000000-0000-0000-0000-000000000301',
  '00000000-0000-0000-0000-000000000102',
  'acme-ops',
  'ACME Operations Ltd',
  'ACME Operations',
  'billing@acme.example',
  'active',
  'US',
  'UTC',
  '{"seeded": true}'::jsonb
)
on conflict (id) do update
set
  subscription_plan_id = excluded.subscription_plan_id,
  legal_name = excluded.legal_name,
  display_name = excluded.display_name,
  billing_email = excluded.billing_email,
  status = excluded.status,
  country_code = excluded.country_code,
  timezone = excluded.timezone,
  metadata = excluded.metadata,
  updated_at = timezone('utc', now());

insert into public.tenant_settings (
  tenant_id,
  default_locale,
  default_timezone,
  retention_days,
  allow_self_service_agent_installation,
  analytics_enabled,
  ai_explanations_enabled,
  settings
) values (
  '00000000-0000-0000-0000-000000000301',
  'en-US',
  'UTC',
  45,
  false,
  true,
  true,
  '{"collection_notice": "Local development policy seed"}'::jsonb
)
on conflict (tenant_id) do update
set
  default_locale = excluded.default_locale,
  default_timezone = excluded.default_timezone,
  retention_days = excluded.retention_days,
  allow_self_service_agent_installation = excluded.allow_self_service_agent_installation,
  analytics_enabled = excluded.analytics_enabled,
  ai_explanations_enabled = excluded.ai_explanations_enabled,
  settings = excluded.settings,
  updated_at = timezone('utc', now());

insert into public.roles (
  id,
  tenant_id,
  slug,
  name,
  description,
  is_system
) values
  (
    '00000000-0000-0000-0000-000000000401',
    '00000000-0000-0000-0000-000000000301',
    'owner',
    'Owner',
    'Full tenant administration rights.',
    true
  ),
  (
    '00000000-0000-0000-0000-000000000402',
    '00000000-0000-0000-0000-000000000301',
    'admin',
    'Admin',
    'Operational administration rights.',
    true
  ),
  (
    '00000000-0000-0000-0000-000000000403',
    '00000000-0000-0000-0000-000000000301',
    'member',
    'Member',
    'Standard tenant member.',
    true
  )
on conflict (id) do update
set
  slug = excluded.slug,
  name = excluded.name,
  description = excluded.description,
  is_system = excluded.is_system,
  updated_at = timezone('utc', now());

insert into public.role_permissions (
  id,
  role_id,
  permission_id
) values
  ('00000000-0000-0000-0000-000000000501', '00000000-0000-0000-0000-000000000401', '00000000-0000-0000-0000-000000000201'),
  ('00000000-0000-0000-0000-000000000502', '00000000-0000-0000-0000-000000000401', '00000000-0000-0000-0000-000000000202'),
  ('00000000-0000-0000-0000-000000000503', '00000000-0000-0000-0000-000000000401', '00000000-0000-0000-0000-000000000203'),
  ('00000000-0000-0000-0000-000000000504', '00000000-0000-0000-0000-000000000401', '00000000-0000-0000-0000-000000000204'),
  ('00000000-0000-0000-0000-000000000505', '00000000-0000-0000-0000-000000000401', '00000000-0000-0000-0000-000000000205'),
  ('00000000-0000-0000-0000-000000000506', '00000000-0000-0000-0000-000000000402', '00000000-0000-0000-0000-000000000202'),
  ('00000000-0000-0000-0000-000000000507', '00000000-0000-0000-0000-000000000402', '00000000-0000-0000-0000-000000000203'),
  ('00000000-0000-0000-0000-000000000508', '00000000-0000-0000-0000-000000000402', '00000000-0000-0000-0000-000000000204'),
  ('00000000-0000-0000-0000-000000000509', '00000000-0000-0000-0000-000000000402', '00000000-0000-0000-0000-000000000205'),
  ('00000000-0000-0000-0000-000000000510', '00000000-0000-0000-0000-000000000403', '00000000-0000-0000-0000-000000000205')
on conflict (role_id, permission_id) do nothing;

insert into public.org_nodes (
  id,
  tenant_id,
  node_key,
  name,
  node_type,
  description,
  metadata
) values
  (
    '00000000-0000-0000-0000-000000000601',
    '00000000-0000-0000-0000-000000000301',
    'root',
    'ACME Operations',
    'company',
    'Root organizational node.',
    '{}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000602',
    '00000000-0000-0000-0000-000000000301',
    'engineering',
    'Engineering',
    'department',
    'Engineering department.',
    '{}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000603',
    '00000000-0000-0000-0000-000000000301',
    'analytics',
    'Analytics',
    'team',
    'Analytics team.',
    '{}'::jsonb
  )
on conflict (id) do update
set
  name = excluded.name,
  node_type = excluded.node_type,
  description = excluded.description,
  metadata = excluded.metadata,
  updated_at = timezone('utc', now());

insert into public.org_edges (
  id,
  tenant_id,
  parent_node_id,
  child_node_id,
  edge_type
) values
  (
    '00000000-0000-0000-0000-000000000701',
    '00000000-0000-0000-0000-000000000301',
    '00000000-0000-0000-0000-000000000601',
    '00000000-0000-0000-0000-000000000602',
    'primary'
  ),
  (
    '00000000-0000-0000-0000-000000000702',
    '00000000-0000-0000-0000-000000000301',
    '00000000-0000-0000-0000-000000000602',
    '00000000-0000-0000-0000-000000000603',
    'primary'
  )
on conflict (tenant_id, parent_node_id, child_node_id) do nothing;

insert into public.employee_profiles (
  id,
  tenant_id,
  org_node_id,
  employee_number,
  full_name,
  work_email,
  employment_status,
  title,
  start_date,
  metadata
) values
  (
    '00000000-0000-0000-0000-000000000801',
    '00000000-0000-0000-0000-000000000301',
    '00000000-0000-0000-0000-000000000603',
    'E-1001',
    'Pat Lee',
    'pat.lee@acme.example',
    'active',
    'Analytics Lead',
    date '2025-01-06',
    '{"seeded": true}'::jsonb
  )
on conflict (id) do update
set
  org_node_id = excluded.org_node_id,
  full_name = excluded.full_name,
  work_email = excluded.work_email,
  employment_status = excluded.employment_status,
  title = excluded.title,
  start_date = excluded.start_date,
  metadata = excluded.metadata,
  updated_at = timezone('utc', now());

insert into public.workstations (
  id,
  tenant_id,
  employee_profile_id,
  hostname,
  os_family,
  serial_number,
  device_fingerprint,
  last_seen_at,
  metadata
) values
  (
    '00000000-0000-0000-0000-000000000901',
    '00000000-0000-0000-0000-000000000301',
    '00000000-0000-0000-0000-000000000801',
    'ACME-WS-001',
    'windows',
    'SN-ACME-001',
    'fingerprint-acme-ws-001',
    timezone('utc', now()),
    '{"seeded": true}'::jsonb
  )
on conflict (id) do update
set
  employee_profile_id = excluded.employee_profile_id,
  hostname = excluded.hostname,
  os_family = excluded.os_family,
  serial_number = excluded.serial_number,
  device_fingerprint = excluded.device_fingerprint,
  last_seen_at = excluded.last_seen_at,
  metadata = excluded.metadata,
  updated_at = timezone('utc', now());

insert into public.agent_installations (
  id,
  tenant_id,
  workstation_id,
  installation_key_hash,
  agent_version,
  osquery_version,
  status,
  last_check_in_at,
  metadata
) values
  (
    '00000000-0000-0000-0000-000000001001',
    '00000000-0000-0000-0000-000000000301',
    '00000000-0000-0000-0000-000000000901',
    'hash-local-dev-installation-001',
    '0.1.0',
    '5.15.0',
    'active',
    timezone('utc', now()),
    '{"seeded": true}'::jsonb
  )
on conflict (id) do update
set
  workstation_id = excluded.workstation_id,
  installation_key_hash = excluded.installation_key_hash,
  agent_version = excluded.agent_version,
  osquery_version = excluded.osquery_version,
  status = excluded.status,
  last_check_in_at = excluded.last_check_in_at,
  metadata = excluded.metadata,
  updated_at = timezone('utc', now());

insert into public.telemetry_policies (
  id,
  tenant_id,
  policy_key,
  name,
  description,
  is_enabled,
  policy_payload,
  version
) values
  (
    '00000000-0000-0000-0000-000000001101',
    '00000000-0000-0000-0000-000000000301',
    'baseline-workstation-observability',
    'Baseline workstation observability',
    'Collect approved osquery telemetry only.',
    true,
    '{
      "allowed_queries": ["os_version", "uptime", "disk_encryption"],
      "forbidden_capture": ["screenshots", "keystrokes", "clipboard"],
      "collection_interval_minutes": 15
    }'::jsonb,
    1
  )
on conflict (id) do update
set
  name = excluded.name,
  description = excluded.description,
  is_enabled = excluded.is_enabled,
  policy_payload = excluded.policy_payload,
  version = excluded.version,
  updated_at = timezone('utc', now());

insert into public.feature_flags (
  id,
  tenant_id,
  flag_key,
  name,
  description,
  enabled,
  variant,
  rollout_rules
) values
  (
    '00000000-0000-0000-0000-000000001201',
    '00000000-0000-0000-0000-000000000301',
    'hierarchical-analytics',
    'Hierarchical analytics',
    'Enable hierarchical rollups in the web control plane.',
    true,
    'general-availability',
    '{}'::jsonb
  )
on conflict (id) do update
set
  name = excluded.name,
  description = excluded.description,
  enabled = excluded.enabled,
  variant = excluded.variant,
  rollout_rules = excluded.rollout_rules,
  updated_at = timezone('utc', now());

insert into public.tenant_usage (
  id,
  tenant_id,
  period_start,
  period_end,
  active_member_count,
  active_workstation_count,
  telemetry_event_count,
  ai_explanation_count,
  storage_bytes,
  usage_payload
) values
  (
    '00000000-0000-0000-0000-000000001301',
    '00000000-0000-0000-0000-000000000301',
    date '2026-04-01',
    date '2026-04-30',
    1,
    1,
    18234,
    77,
    104857600,
    '{"events_per_day": 608}'::jsonb
  )
on conflict (id) do update
set
  period_start = excluded.period_start,
  period_end = excluded.period_end,
  active_member_count = excluded.active_member_count,
  active_workstation_count = excluded.active_workstation_count,
  telemetry_event_count = excluded.telemetry_event_count,
  ai_explanation_count = excluded.ai_explanation_count,
  storage_bytes = excluded.storage_bytes,
  usage_payload = excluded.usage_payload,
  updated_at = timezone('utc', now());

do $$
declare
  v_user_id uuid;
begin
  select id
    into v_user_id
  from auth.users
  order by created_at
  limit 1;

  if v_user_id is not null then
    insert into public.user_profiles (
      user_id,
      primary_email,
      display_name,
      locale,
      timezone,
      metadata
    )
    select
      u.id,
      u.email,
      coalesce(u.raw_user_meta_data ->> 'full_name', 'Local Owner'),
      'en-US',
      'UTC',
      '{"seeded": true}'::jsonb
    from auth.users u
    where u.id = v_user_id
    on conflict (user_id) do update
    set
      primary_email = excluded.primary_email,
      display_name = excluded.display_name,
      locale = excluded.locale,
      timezone = excluded.timezone,
      metadata = excluded.metadata,
      updated_at = timezone('utc', now());

    insert into public.memberships (
      id,
      tenant_id,
      user_id,
      role_id,
      status,
      joined_at,
      metadata
    ) values (
      '00000000-0000-0000-0000-000000001401',
      '00000000-0000-0000-0000-000000000301',
      v_user_id,
      '00000000-0000-0000-0000-000000000401',
      'active',
      timezone('utc', now()),
      '{"seeded": true}'::jsonb
    )
    on conflict (tenant_id, user_id) do update
    set
      role_id = excluded.role_id,
      status = excluded.status,
      joined_at = excluded.joined_at,
      metadata = excluded.metadata,
      updated_at = timezone('utc', now());

    update public.employee_profiles
    set membership_id = '00000000-0000-0000-0000-000000001401',
        updated_at = timezone('utc', now())
    where id = '00000000-0000-0000-0000-000000000801'
      and membership_id is distinct from '00000000-0000-0000-0000-000000001401';
  end if;
end
$$;

