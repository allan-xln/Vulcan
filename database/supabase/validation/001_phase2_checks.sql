do $$
declare
  v_missing_tables text[];
  v_missing_policies text[];
begin
  select array_agg(expected_table)
    into v_missing_tables
  from (
    select unnest(array[
      'subscription_plans',
      'tenants',
      'tenant_settings',
      'user_profiles',
      'permissions',
      'roles',
      'role_permissions',
      'memberships',
      'membership_closure',
      'departments',
      'devices',
      'activity_events',
      'operational_metrics',
      'ai_insights',
      'notifications',
      'notification_preferences',
      'ai_provider_configs',
      'org_nodes',
      'org_edges',
      'org_closure',
      'employee_profiles',
      'workstations',
      'agent_installations',
      'operational_event_policies',
      'feature_flags',
      'audit_logs',
      'tenant_usage'
    ]) as expected_table
  ) expected
  where not exists (
    select 1
    from information_schema.tables t
    where t.table_schema = 'public'
      and t.table_name = expected.expected_table
  );

  if v_missing_tables is not null then
    raise exception 'missing public tables: %', array_to_string(v_missing_tables, ', ');
  end if;

  select array_agg(expected_policy)
    into v_missing_policies
  from (
    select unnest(array[
      'tenants_read_member',
      'tenant_settings_manage_admin',
      'user_profiles_self_read',
      'roles_manage_admin',
      'memberships_manage_admin',
      'memberships_read_hierarchy',
      'membership_closure_read_member',
      'devices_read_hierarchy',
      'activity_events_read_hierarchy',
      'metrics_read_hierarchy',
      'insights_read_hierarchy',
      'notifications_read_recipient_or_admin',
      'org_closure_read_member',
      'audit_logs_read_member'
    ]) as expected_policy
  ) expected
  where not exists (
    select 1
    from pg_policies p
    where p.schemaname = 'public'
      and p.policyname = expected.expected_policy
  );

  if v_missing_policies is not null then
    raise exception 'missing RLS policies: %', array_to_string(v_missing_policies, ', ');
  end if;

  if exists (
    select 1
    from (
      select unnest(array[
        'tenants',
        'departments',
        'roles',
        'user_profiles',
        'memberships',
        'membership_closure',
        'devices',
        'activity_events',
        'operational_metrics',
        'ai_insights',
        'notifications',
        'notification_preferences',
        'ai_provider_configs',
        'audit_logs'
      ]) as table_name
    ) expected
    join pg_class c on c.relname = expected.table_name
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
    where not c.relrowsecurity
  ) then
    raise exception 'one or more current Vulcan business tables do not have RLS enabled';
  end if;
end
$$;

select
  (select count(*) from public.tenants) as tenant_count,
  (select count(*) from public.roles) as role_count,
  (select count(*) from public.permissions) as permission_count,
  (select count(*) from public.org_nodes) as org_node_count,
  (select count(*) from public.feature_flags) as feature_flag_count,
  (select count(*) from public.membership_closure) as membership_closure_count,
  (select count(*) from public.devices) as device_count,
  (select count(*) from public.activity_events) as activity_event_count;
