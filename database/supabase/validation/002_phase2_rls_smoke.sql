begin;

do $$
declare
  v_user_id uuid;
  v_tenant_id uuid;
  v_membership_id uuid;
begin
  select membership.user_id, membership.tenant_id, membership.id
    into v_user_id, v_tenant_id, v_membership_id
  from public.memberships membership
  left join public.roles role on role.id = membership.role_id
  where membership.status = 'active'
    and not exists (
      select 1
      from public.vulcan_root_users root_user
      where root_user.user_id = membership.user_id
    )
  order by
    case coalesce(role.scope, 'self')
      when 'tenant' then 0
      when 'global' then 1
      when 'hierarchy' then 2
      else 3
    end,
    membership.created_at
  limit 1;

  if v_user_id is null then
    raise exception 'RLS smoke requires at least one active membership. Run seed:demo or create a tenant admin first.';
  end if;

  perform set_config('request.jwt.claim.sub', v_user_id::text, true);
  perform set_config('request.jwt.claim.role', 'authenticated', true);
  perform set_config('vulcan.rls_test_user_id', v_user_id::text, true);
  perform set_config('vulcan.rls_test_tenant_id', v_tenant_id::text, true);
  perform set_config('vulcan.rls_test_membership_id', v_membership_id::text, true);

  insert into public.tenants (id, slug, legal_name, display_name, status, plan, region, metadata)
  values (
    '00000000-0000-0000-0000-00000000f999',
    'vulcan-rls-isolation-smoke',
    'Vulcan RLS Isolation Smoke',
    'Vulcan RLS Isolation Smoke',
    'active',
    'growth',
    'global',
    '{"temporary": true}'::jsonb
  )
  on conflict (id) do nothing;

  insert into public.devices (
    id,
    tenant_id,
    owner_membership_id,
    hostname,
    os,
    device_fingerprint,
    status,
    metadata
  )
  values (
    '00000000-0000-0000-0000-00000000f901',
    '00000000-0000-0000-0000-00000000f999',
    null,
    'RLS-FOREIGN-UNASSIGNED',
    'Linux',
    'rls-foreign-unassigned-device',
    'online',
    '{"temporary": true}'::jsonb
  )
  on conflict (id) do nothing;

  insert into public.activity_events (
    id,
    tenant_id,
    membership_id,
    device_id,
    event_type,
    app_name,
    category,
    duration_seconds,
    occurred_at,
    metadata
  )
  values (
    '00000000-0000-0000-0000-00000000f902',
    '00000000-0000-0000-0000-00000000f999',
    null,
    '00000000-0000-0000-0000-00000000f901',
    'app_focus_started',
    'RLS Foreign App',
    'smoke',
    60,
    timezone('utc', now()),
    '{"temporary": true}'::jsonb
  )
  on conflict (id) do nothing;

  insert into public.operational_metrics (
    id,
    tenant_id,
    membership_id,
    metric_key,
    metric_label,
    value_numeric,
    period_start,
    period_end,
    metadata
  )
  values (
    '00000000-0000-0000-0000-00000000f903',
    '00000000-0000-0000-0000-00000000f999',
    null,
    'rls_foreign_metric',
    'RLS Foreign Metric',
    1,
    timezone('utc', now()),
    timezone('utc', now()),
    '{"temporary": true}'::jsonb
  )
  on conflict (id) do nothing;

  insert into public.ai_insights (
    id,
    tenant_id,
    membership_id,
    source_route,
    title,
    summary,
    impact,
    metadata
  )
  values (
    '00000000-0000-0000-0000-00000000f904',
    '00000000-0000-0000-0000-00000000f999',
    null,
    'rules',
    'RLS Foreign Insight',
    'This row must not be visible outside its tenant.',
    'low',
    '{"temporary": true}'::jsonb
  )
  on conflict (id) do nothing;

  insert into public.whatsapp_delivery_queue (
    id,
    tenant_id,
    recipient_membership_id,
    notification_type,
    root_channel_name,
    root_channel_number,
    destination,
    title,
    message,
    status,
    provider,
    payload
  )
  values (
    '00000000-0000-0000-0000-00000000f905',
    '00000000-0000-0000-0000-00000000f999',
    null,
    'alerta',
    'RLS Smoke',
    '5500000000000',
    '5500000000000',
    'RLS Foreign WhatsApp',
    'This row must not be visible outside its tenant.',
    'queued',
    'smoke',
    '{"temporary": true}'::jsonb
  )
  on conflict (id) do nothing;

  insert into public.whatsapp_delivery_logs (
    id,
    tenant_id,
    queue_id,
    recipient_membership_id,
    destination,
    status,
    provider,
    provider_result,
    payload
  )
  values (
    '00000000-0000-0000-0000-00000000f906',
    '00000000-0000-0000-0000-00000000f999',
    '00000000-0000-0000-0000-00000000f905',
    null,
    '5500000000000',
    'queued',
    'smoke',
    'smoke',
    '{"temporary": true}'::jsonb
  )
  on conflict (id) do nothing;
end
$$;

set local role authenticated;

do $$
declare
  v_user_id uuid := current_setting('vulcan.rls_test_user_id')::uuid;
  v_tenant_id uuid := current_setting('vulcan.rls_test_tenant_id')::uuid;
  v_membership_id uuid := current_setting('vulcan.rls_test_membership_id')::uuid;
  v_visible_tenants integer;
  v_foreign_tenants integer;
  v_visible_memberships integer;
  v_outside_memberships integer;
  v_visible_closure integer;
  v_visible_devices integer;
  v_visible_events integer;
  v_visible_audit_logs integer;
begin
  select count(*) into v_visible_tenants
  from public.tenants;

  if v_visible_tenants <> 1 then
    raise exception 'expected authenticated seeded user to see 1 tenant, saw %', v_visible_tenants;
  end if;

  select count(*) into v_foreign_tenants
  from public.tenants
  where id <> v_tenant_id;

  if v_foreign_tenants <> 0 then
    raise exception 'RLS leak: authenticated user saw % tenant(s) outside assigned tenant', v_foreign_tenants;
  end if;

  if exists (
    select 1
    from public.tenants
    where id = '00000000-0000-0000-0000-00000000f999'
  ) then
    raise exception 'RLS leak: authenticated user saw isolated smoke tenant';
  end if;

  select count(*) into v_visible_memberships
  from public.memberships;

  if v_visible_memberships < 1 then
    raise exception 'expected authenticated seeded user to see at least itself in memberships';
  end if;

  select count(*) into v_outside_memberships
  from public.memberships
  where tenant_id <> v_tenant_id;

  if v_outside_memberships <> 0 then
    raise exception 'RLS leak: authenticated user saw % membership(s) outside assigned tenant', v_outside_memberships;
  end if;

  if not exists (
    select 1
    from public.memberships
    where id = v_membership_id
      and user_id = v_user_id
      and tenant_id = v_tenant_id
  ) then
    raise exception 'expected authenticated seeded user membership to be visible';
  end if;

  select count(*) into v_visible_closure
  from public.membership_closure
  where tenant_id <> v_tenant_id;

  if v_visible_closure <> 0 then
    raise exception 'RLS leak: authenticated user saw % closure rows outside assigned tenant', v_visible_closure;
  end if;

  select count(*) into v_visible_devices
  from public.devices
  where tenant_id <> v_tenant_id;

  if v_visible_devices <> 0 then
    raise exception 'RLS leak: authenticated user saw % device(s) outside assigned tenant', v_visible_devices;
  end if;

  if exists (
    select 1
    from public.devices
    where id = '00000000-0000-0000-0000-00000000f901'
  ) then
    raise exception 'RLS leak: authenticated user saw foreign unassigned device';
  end if;

  select count(*) into v_visible_events
  from public.activity_events
  where tenant_id <> v_tenant_id;

  if v_visible_events <> 0 then
    raise exception 'RLS leak: authenticated user saw % activity event(s) outside assigned tenant', v_visible_events;
  end if;

  if exists (
    select 1
    from public.activity_events
    where id = '00000000-0000-0000-0000-00000000f902'
  ) then
    raise exception 'RLS leak: authenticated user saw foreign unassigned activity event';
  end if;

  if exists (
    select 1
    from public.operational_metrics
    where id = '00000000-0000-0000-0000-00000000f903'
  ) then
    raise exception 'RLS leak: authenticated user saw foreign unassigned operational metric';
  end if;

  if exists (
    select 1
    from public.ai_insights
    where id = '00000000-0000-0000-0000-00000000f904'
  ) then
    raise exception 'RLS leak: authenticated user saw foreign unassigned AI insight';
  end if;

  if exists (
    select 1
    from public.whatsapp_delivery_queue
    where id = '00000000-0000-0000-0000-00000000f905'
  ) then
    raise exception 'RLS leak: authenticated user saw foreign WhatsApp queue row';
  end if;

  if exists (
    select 1
    from public.whatsapp_delivery_logs
    where id = '00000000-0000-0000-0000-00000000f906'
  ) then
    raise exception 'RLS leak: authenticated user saw foreign WhatsApp delivery log';
  end if;

  select count(*) into v_visible_audit_logs
  from public.audit_logs;

  if exists (
    select 1
    from public.audit_logs
    where tenant_id is not null
      and tenant_id <> v_tenant_id
  ) then
    raise exception 'RLS leak: authenticated user saw audit logs outside assigned tenant';
  end if;
end
$$;

rollback;
