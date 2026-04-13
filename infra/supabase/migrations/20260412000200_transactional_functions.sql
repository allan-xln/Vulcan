create or replace function app_private.set_audit_fields()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'INSERT' then
    if new.created_at is null then
      new.created_at := timezone('utc', now());
    end if;

    if new.updated_at is null then
      new.updated_at := timezone('utc', now());
    end if;

    if to_jsonb(new) ? 'created_by' and new.created_by is null and auth.uid() is not null then
      new.created_by := auth.uid();
    end if;
  end if;

  if to_jsonb(new) ? 'updated_at' then
    new.updated_at := timezone('utc', now());
  end if;

  if to_jsonb(new) ? 'updated_by' and auth.uid() is not null then
    new.updated_by := auth.uid();
  end if;

  return new;
end;
$$;

create or replace function public.is_tenant_member(p_tenant_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.memberships m
    where m.tenant_id = p_tenant_id
      and m.user_id = auth.uid()
      and m.status = 'active'::public.membership_status
  );
$$;

create or replace function public.has_tenant_role(
  p_tenant_id uuid,
  p_role_slugs text[]
)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.memberships m
    join public.roles r on r.id = m.role_id
    where m.tenant_id = p_tenant_id
      and m.user_id = auth.uid()
      and m.status = 'active'::public.membership_status
      and r.slug = any (p_role_slugs)
  );
$$;

create or replace function public.can_manage_tenant(p_tenant_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select public.has_tenant_role(p_tenant_id, array['owner', 'admin']);
$$;

create or replace function app_private.write_audit_log()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_row jsonb;
  v_old jsonb;
  v_new jsonb;
  v_tenant_id uuid;
  v_entity_id uuid;
  v_actor_membership_id uuid;
begin
  if tg_op = 'DELETE' then
    v_row := to_jsonb(old);
    v_old := to_jsonb(old);
    v_new := null;
  else
    v_row := to_jsonb(new);
    v_old := case when tg_op = 'UPDATE' then to_jsonb(old) else null end;
    v_new := to_jsonb(new);
  end if;

  v_tenant_id := case
    when v_row ? 'tenant_id' then nullif(v_row ->> 'tenant_id', '')::uuid
    when tg_table_name = 'tenants' then nullif(v_row ->> 'id', '')::uuid
    else null
  end;

  if v_tenant_id is null and tg_table_name = 'role_permissions' and (v_row ? 'role_id') then
    select r.tenant_id
      into v_tenant_id
    from public.roles r
    where r.id = nullif(v_row ->> 'role_id', '')::uuid;
  end if;

  if v_tenant_id is null then
    return coalesce(new, old);
  end if;

  v_entity_id := case
    when v_row ? 'id' then nullif(v_row ->> 'id', '')::uuid
    when v_row ? 'tenant_id' then nullif(v_row ->> 'tenant_id', '')::uuid
    else null
  end;

  select m.id
    into v_actor_membership_id
  from public.memberships m
  where m.tenant_id = v_tenant_id
    and m.user_id = auth.uid()
    and m.status = 'active'::public.membership_status
  order by m.created_at
  limit 1;

  insert into public.audit_logs (
    tenant_id,
    actor_user_id,
    actor_membership_id,
    action,
    entity_table,
    entity_id,
    change_summary,
    request_context
  ) values (
    v_tenant_id,
    auth.uid(),
    v_actor_membership_id,
    lower(tg_op),
    tg_table_name,
    v_entity_id,
    jsonb_build_object(
      'old', coalesce(v_old, '{}'::jsonb),
      'new', coalesce(v_new, '{}'::jsonb)
    ),
    jsonb_build_object(
      'trigger_name', tg_name,
      'schema', tg_table_schema
    )
  );

  return coalesce(new, old);
end;
$$;

create or replace function app_private.validate_membership_role_tenant()
returns trigger
language plpgsql
as $$
declare
  v_role_tenant_id uuid;
begin
  select r.tenant_id
    into v_role_tenant_id
  from public.roles r
  where r.id = new.role_id;

  if v_role_tenant_id is null then
    raise exception 'membership role_id % does not exist', new.role_id;
  end if;

  if v_role_tenant_id <> new.tenant_id then
    raise exception 'membership role tenant mismatch';
  end if;

  return new;
end;
$$;

create or replace function app_private.validate_org_edge()
returns trigger
language plpgsql
as $$
declare
  v_parent_tenant_id uuid;
  v_child_tenant_id uuid;
  v_cycle_found boolean;
begin
  select tenant_id into v_parent_tenant_id
  from public.org_nodes
  where id = new.parent_node_id;

  select tenant_id into v_child_tenant_id
  from public.org_nodes
  where id = new.child_node_id;

  if v_parent_tenant_id is null or v_child_tenant_id is null then
    raise exception 'org edge nodes must exist';
  end if;

  if new.tenant_id <> v_parent_tenant_id or new.tenant_id <> v_child_tenant_id then
    raise exception 'org edge tenant mismatch';
  end if;

  with recursive path(node_id) as (
    select new.child_node_id
    union all
    select e.child_node_id
    from public.org_edges e
    join path p on p.node_id = e.parent_node_id
    where e.tenant_id = new.tenant_id
      and (tg_op = 'INSERT' or e.id <> new.id)
  )
  select exists (
    select 1
    from path
    where node_id = new.parent_node_id
  )
  into v_cycle_found;

  if v_cycle_found then
    raise exception 'org edge would create a cycle';
  end if;

  return new;
end;
$$;

create or replace function app_private.rebuild_org_closure_for_tenant(p_tenant_id uuid)
returns void
language plpgsql
as $$
begin
  delete from public.org_closure
  where tenant_id = p_tenant_id;

  insert into public.org_closure (
    tenant_id,
    ancestor_node_id,
    descendant_node_id,
    depth,
    created_at
  )
  with recursive hierarchy as (
    select
      n.tenant_id,
      n.id as ancestor_node_id,
      n.id as descendant_node_id,
      0 as depth
    from public.org_nodes n
    where n.tenant_id = p_tenant_id

    union all

    select
      h.tenant_id,
      h.ancestor_node_id,
      e.child_node_id,
      h.depth + 1
    from hierarchy h
    join public.org_edges e
      on e.tenant_id = h.tenant_id
     and e.parent_node_id = h.descendant_node_id
  )
  select distinct
    tenant_id,
    ancestor_node_id,
    descendant_node_id,
    depth,
    timezone('utc', now())
  from hierarchy;
end;
$$;

create or replace function app_private.sync_org_closure()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'DELETE' then
    perform app_private.rebuild_org_closure_for_tenant(old.tenant_id);
    return old;
  end if;

  if tg_op = 'UPDATE' and old.tenant_id <> new.tenant_id then
    perform app_private.rebuild_org_closure_for_tenant(old.tenant_id);
  end if;

  perform app_private.rebuild_org_closure_for_tenant(new.tenant_id);
  return new;
end;
$$;

drop trigger if exists trg_subscription_plans_set_audit_fields on public.subscription_plans;
create trigger trg_subscription_plans_set_audit_fields
before insert or update on public.subscription_plans
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_tenants_set_audit_fields on public.tenants;
create trigger trg_tenants_set_audit_fields
before insert or update on public.tenants
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_tenant_settings_set_audit_fields on public.tenant_settings;
create trigger trg_tenant_settings_set_audit_fields
before insert or update on public.tenant_settings
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_permissions_set_audit_fields on public.permissions;
create trigger trg_permissions_set_audit_fields
before insert or update on public.permissions
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_roles_set_audit_fields on public.roles;
create trigger trg_roles_set_audit_fields
before insert or update on public.roles
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_role_permissions_set_audit_fields on public.role_permissions;
create trigger trg_role_permissions_set_audit_fields
before insert or update on public.role_permissions
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_memberships_set_audit_fields on public.memberships;
create trigger trg_memberships_set_audit_fields
before insert or update on public.memberships
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_org_nodes_set_audit_fields on public.org_nodes;
create trigger trg_org_nodes_set_audit_fields
before insert or update on public.org_nodes
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_org_edges_set_audit_fields on public.org_edges;
create trigger trg_org_edges_set_audit_fields
before insert or update on public.org_edges
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_employee_profiles_set_audit_fields on public.employee_profiles;
create trigger trg_employee_profiles_set_audit_fields
before insert or update on public.employee_profiles
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_workstations_set_audit_fields on public.workstations;
create trigger trg_workstations_set_audit_fields
before insert or update on public.workstations
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_agent_installations_set_audit_fields on public.agent_installations;
create trigger trg_agent_installations_set_audit_fields
before insert or update on public.agent_installations
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_telemetry_policies_set_audit_fields on public.telemetry_policies;
create trigger trg_telemetry_policies_set_audit_fields
before insert or update on public.telemetry_policies
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_feature_flags_set_audit_fields on public.feature_flags;
create trigger trg_feature_flags_set_audit_fields
before insert or update on public.feature_flags
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_tenant_usage_set_audit_fields on public.tenant_usage;
create trigger trg_tenant_usage_set_audit_fields
before insert or update on public.tenant_usage
for each row execute function app_private.set_audit_fields();

drop trigger if exists trg_memberships_validate_role_tenant on public.memberships;
create trigger trg_memberships_validate_role_tenant
before insert or update on public.memberships
for each row execute function app_private.validate_membership_role_tenant();

drop trigger if exists trg_org_edges_validate on public.org_edges;
create trigger trg_org_edges_validate
before insert or update on public.org_edges
for each row execute function app_private.validate_org_edge();

drop trigger if exists trg_org_nodes_sync_closure on public.org_nodes;
create trigger trg_org_nodes_sync_closure
after insert or update or delete on public.org_nodes
for each row execute function app_private.sync_org_closure();

drop trigger if exists trg_org_edges_sync_closure on public.org_edges;
create trigger trg_org_edges_sync_closure
after insert or update or delete on public.org_edges
for each row execute function app_private.sync_org_closure();

drop trigger if exists trg_tenants_audit on public.tenants;
create trigger trg_tenants_audit
after insert or update or delete on public.tenants
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_tenant_settings_audit on public.tenant_settings;
create trigger trg_tenant_settings_audit
after insert or update or delete on public.tenant_settings
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_roles_audit on public.roles;
create trigger trg_roles_audit
after insert or update or delete on public.roles
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_role_permissions_audit on public.role_permissions;
create trigger trg_role_permissions_audit
after insert or update or delete on public.role_permissions
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_memberships_audit on public.memberships;
create trigger trg_memberships_audit
after insert or update or delete on public.memberships
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_org_nodes_audit on public.org_nodes;
create trigger trg_org_nodes_audit
after insert or update or delete on public.org_nodes
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_org_edges_audit on public.org_edges;
create trigger trg_org_edges_audit
after insert or update or delete on public.org_edges
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_employee_profiles_audit on public.employee_profiles;
create trigger trg_employee_profiles_audit
after insert or update or delete on public.employee_profiles
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_workstations_audit on public.workstations;
create trigger trg_workstations_audit
after insert or update or delete on public.workstations
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_agent_installations_audit on public.agent_installations;
create trigger trg_agent_installations_audit
after insert or update or delete on public.agent_installations
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_telemetry_policies_audit on public.telemetry_policies;
create trigger trg_telemetry_policies_audit
after insert or update or delete on public.telemetry_policies
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_feature_flags_audit on public.feature_flags;
create trigger trg_feature_flags_audit
after insert or update or delete on public.feature_flags
for each row execute function app_private.write_audit_log();

drop trigger if exists trg_tenant_usage_audit on public.tenant_usage;
create trigger trg_tenant_usage_audit
after insert or update or delete on public.tenant_usage
for each row execute function app_private.write_audit_log();
