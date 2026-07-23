begin;

do $$
declare
  v_user_id uuid;
  v_tenant_id uuid;
begin
  select membership.user_id, membership.tenant_id
    into v_user_id, v_tenant_id
  from public.memberships membership
  join public.roles role on role.id = membership.role_id
  where membership.status = 'active'
    and role.scope in ('tenant', 'global')
    and not exists (
      select 1
      from public.vulcan_root_users root_user
      where root_user.user_id = membership.user_id
    )
  order by membership.created_at
  limit 1;

  if v_user_id is null then
    v_user_id := '00000000-0000-0000-0000-00000000f710';
    v_tenant_id := '00000000-0000-0000-0000-00000000f711';

    insert into auth.users (id, email)
    values (v_user_id, 'platform-rls-validation@vulcan.local');

    insert into public.tenants (id, slug, legal_name, display_name, status, plan, region, metadata)
    values (
      v_tenant_id,
      'vulcan-platform-rls-owner',
      'Vulcan Platform RLS Owner',
      'Vulcan Platform RLS Owner',
      'active',
      'growth',
      'global',
      '{"temporary": true}'::jsonb
    );

    insert into public.roles (id, tenant_id, slug, name, scope, is_system)
    values (
      '00000000-0000-0000-0000-00000000f712',
      v_tenant_id,
      'platform-rls-admin',
      'Platform RLS Admin',
      'tenant',
      false
    );

    insert into public.memberships (
      id,
      tenant_id,
      user_id,
      role_id,
      status,
      full_name,
      work_email,
      hierarchy_level
    )
    values (
      '00000000-0000-0000-0000-00000000f713',
      v_tenant_id,
      v_user_id,
      '00000000-0000-0000-0000-00000000f712',
      'active',
      'Platform RLS Validator',
      'platform-rls-validation@vulcan.local',
      0
    );
  end if;

  perform set_config('request.jwt.claim.sub', v_user_id::text, true);
  perform set_config('request.jwt.claim.role', 'authenticated', true);
  perform set_config('vulcan.platform_test_tenant_id', v_tenant_id::text, true);

  insert into public.sites (id, tenant_id, code, name)
  values (
    '00000000-0000-0000-0000-00000000f801',
    v_tenant_id,
    'RLS-OWN',
    'RLS Own Site'
  );

  insert into public.unified_events (
    id,
    tenant_id,
    source,
    source_type,
    source_event_id,
    event_type,
    category,
    occurred_at,
    message,
    fingerprint,
    trusted_origin
  )
  values (
    '00000000-0000-0000-0000-00000000f802',
    v_tenant_id,
    'rls-validation',
    'test',
    'rls-own-event',
    'test.own',
    'test',
    timezone('utc', now()),
    'Own tenant event.',
    'rls-own-event',
    true
  );

  insert into public.tenants (id, slug, legal_name, display_name, status, plan, region, metadata)
  values (
    '00000000-0000-0000-0000-00000000f999',
    'vulcan-platform-rls-foreign',
    'Vulcan Platform RLS Foreign',
    'Vulcan Platform RLS Foreign',
    'active',
    'growth',
    'global',
    '{"temporary": true}'::jsonb
  )
  on conflict (id) do nothing;

  insert into public.tenant_modules (tenant_id, module_key, enabled)
  values ('00000000-0000-0000-0000-00000000f999', 'workforce', true)
  on conflict (tenant_id, module_key) do update
  set enabled = excluded.enabled;

  insert into public.sites (id, tenant_id, code, name)
  values (
    '00000000-0000-0000-0000-00000000f901',
    '00000000-0000-0000-0000-00000000f999',
    'RLS-FOREIGN',
    'RLS Foreign Site'
  );

  insert into public.infrastructure_networks (
    id,
    tenant_id,
    site_id,
    name,
    network_cidr
  )
  values (
    '00000000-0000-0000-0000-00000000f902',
    '00000000-0000-0000-0000-00000000f999',
    '00000000-0000-0000-0000-00000000f901',
    'RLS Foreign Network',
    '10.255.255.0/28'
  );

  insert into public.infrastructure_assets (
    id,
    tenant_id,
    site_id,
    network_id,
    asset_type,
    name
  )
  values (
    '00000000-0000-0000-0000-00000000f903',
    '00000000-0000-0000-0000-00000000f999',
    '00000000-0000-0000-0000-00000000f901',
    '00000000-0000-0000-0000-00000000f902',
    'server',
    'RLS Foreign Asset'
  );

  insert into public.discovery_policies (
    id,
    tenant_id,
    site_id,
    name,
    allowed_networks
  )
  values (
    '00000000-0000-0000-0000-00000000f904',
    '00000000-0000-0000-0000-00000000f999',
    '00000000-0000-0000-0000-00000000f901',
    'RLS Foreign Discovery',
    array['10.255.255.0/28'::cidr]
  );

  insert into public.unified_events (
    id,
    tenant_id,
    site_id,
    asset_id,
    source,
    source_type,
    source_event_id,
    event_type,
    category,
    occurred_at,
    message,
    fingerprint,
    trusted_origin
  )
  values (
    '00000000-0000-0000-0000-00000000f905',
    '00000000-0000-0000-0000-00000000f999',
    '00000000-0000-0000-0000-00000000f901',
    '00000000-0000-0000-0000-00000000f903',
    'rls-validation',
    'test',
    'rls-foreign-event',
    'test.foreign',
    'test',
    timezone('utc', now()),
    'Foreign tenant event.',
    'rls-foreign-event',
    true
  );
end
$$;

set local role authenticated;

do $$
declare
  v_tenant_id uuid := current_setting('vulcan.platform_test_tenant_id')::uuid;
begin
  if not exists (
    select 1
    from public.sites
    where id = '00000000-0000-0000-0000-00000000f801'
      and tenant_id = v_tenant_id
  ) then
    raise exception 'platform RLS validation could not see active tenant site';
  end if;

  if not exists (
    select 1
    from public.unified_events
    where id = '00000000-0000-0000-0000-00000000f802'
      and tenant_id = v_tenant_id
  ) then
    raise exception 'platform RLS validation could not see active tenant event';
  end if;

  if exists (
    select 1
    from public.tenant_modules
    where tenant_id = '00000000-0000-0000-0000-00000000f999'
  ) then
    raise exception 'RLS leak: foreign tenant module is visible';
  end if;

  if exists (
    select 1
    from public.sites
    where tenant_id = '00000000-0000-0000-0000-00000000f999'
  ) then
    raise exception 'RLS leak: foreign site is visible';
  end if;

  if exists (
    select 1
    from public.infrastructure_networks
    where tenant_id = '00000000-0000-0000-0000-00000000f999'
  ) then
    raise exception 'RLS leak: foreign network is visible';
  end if;

  if exists (
    select 1
    from public.infrastructure_assets
    where tenant_id = '00000000-0000-0000-0000-00000000f999'
  ) then
    raise exception 'RLS leak: foreign asset is visible';
  end if;

  if exists (
    select 1
    from public.discovery_policies
    where tenant_id = '00000000-0000-0000-0000-00000000f999'
  ) then
    raise exception 'RLS leak: foreign discovery policy is visible';
  end if;

  if exists (
    select 1
    from public.unified_events
    where tenant_id = '00000000-0000-0000-0000-00000000f999'
  ) then
    raise exception 'RLS leak: foreign unified event is visible';
  end if;

  if exists (
    select 1
    from public.audit_logs
    where tenant_id = '00000000-0000-0000-0000-00000000f999'
  ) then
    raise exception 'RLS leak: foreign platform audit is visible';
  end if;
end
$$;

reset role;

do $$
declare
  v_missing_rls integer;
begin
  select count(*)
    into v_missing_rls
  from pg_tables
  where schemaname = 'public'
    and tablename = any(array[
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
      'discovery_findings',
      'unified_events',
      'incidents',
      'incident_events',
      'retention_policies'
    ])
    and not rowsecurity;

  if v_missing_rls <> 0 then
    raise exception 'platform RLS disabled on % table(s)', v_missing_rls;
  end if;
end
$$;

rollback;
