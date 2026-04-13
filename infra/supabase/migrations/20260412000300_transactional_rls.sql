alter table public.subscription_plans enable row level security;
alter table public.tenants enable row level security;
alter table public.tenant_settings enable row level security;
alter table public.user_profiles enable row level security;
alter table public.permissions enable row level security;
alter table public.roles enable row level security;
alter table public.role_permissions enable row level security;
alter table public.memberships enable row level security;
alter table public.org_nodes enable row level security;
alter table public.org_edges enable row level security;
alter table public.org_closure enable row level security;
alter table public.employee_profiles enable row level security;
alter table public.workstations enable row level security;
alter table public.agent_installations enable row level security;
alter table public.telemetry_policies enable row level security;
alter table public.feature_flags enable row level security;
alter table public.audit_logs enable row level security;
alter table public.tenant_usage enable row level security;

drop policy if exists subscription_plans_read_authenticated on public.subscription_plans;
create policy subscription_plans_read_authenticated
on public.subscription_plans
for select
to authenticated
using (true);

drop policy if exists tenants_read_member on public.tenants;
create policy tenants_read_member
on public.tenants
for select
to authenticated
using (public.is_tenant_member(id));

drop policy if exists tenants_manage_admin on public.tenants;
create policy tenants_manage_admin
on public.tenants
for update
to authenticated
using (public.can_manage_tenant(id))
with check (public.can_manage_tenant(id));

drop policy if exists tenant_settings_read_member on public.tenant_settings;
create policy tenant_settings_read_member
on public.tenant_settings
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists tenant_settings_manage_admin on public.tenant_settings;
create policy tenant_settings_manage_admin
on public.tenant_settings
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

drop policy if exists user_profiles_self_read on public.user_profiles;
create policy user_profiles_self_read
on public.user_profiles
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists user_profiles_self_insert on public.user_profiles;
create policy user_profiles_self_insert
on public.user_profiles
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists user_profiles_self_update on public.user_profiles;
create policy user_profiles_self_update
on public.user_profiles
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists permissions_read_authenticated on public.permissions;
create policy permissions_read_authenticated
on public.permissions
for select
to authenticated
using (true);

drop policy if exists roles_read_member on public.roles;
create policy roles_read_member
on public.roles
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists roles_manage_admin on public.roles;
create policy roles_manage_admin
on public.roles
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

drop policy if exists role_permissions_read_member on public.role_permissions;
create policy role_permissions_read_member
on public.role_permissions
for select
to authenticated
using (
  exists (
    select 1
    from public.roles r
    where r.id = role_permissions.role_id
      and public.is_tenant_member(r.tenant_id)
  )
);

drop policy if exists role_permissions_manage_admin on public.role_permissions;
create policy role_permissions_manage_admin
on public.role_permissions
for all
to authenticated
using (
  exists (
    select 1
    from public.roles r
    where r.id = role_permissions.role_id
      and public.can_manage_tenant(r.tenant_id)
  )
)
with check (
  exists (
    select 1
    from public.roles r
    where r.id = role_permissions.role_id
      and public.can_manage_tenant(r.tenant_id)
  )
);

drop policy if exists memberships_read_member on public.memberships;
create policy memberships_read_member
on public.memberships
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists memberships_manage_admin on public.memberships;
create policy memberships_manage_admin
on public.memberships
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

drop policy if exists org_nodes_read_member on public.org_nodes;
create policy org_nodes_read_member
on public.org_nodes
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists org_nodes_manage_admin on public.org_nodes;
create policy org_nodes_manage_admin
on public.org_nodes
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

drop policy if exists org_edges_read_member on public.org_edges;
create policy org_edges_read_member
on public.org_edges
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists org_edges_manage_admin on public.org_edges;
create policy org_edges_manage_admin
on public.org_edges
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

drop policy if exists org_closure_read_member on public.org_closure;
create policy org_closure_read_member
on public.org_closure
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists employee_profiles_read_member on public.employee_profiles;
create policy employee_profiles_read_member
on public.employee_profiles
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists employee_profiles_manage_admin on public.employee_profiles;
create policy employee_profiles_manage_admin
on public.employee_profiles
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

drop policy if exists workstations_read_member on public.workstations;
create policy workstations_read_member
on public.workstations
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists workstations_manage_admin on public.workstations;
create policy workstations_manage_admin
on public.workstations
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

drop policy if exists agent_installations_read_member on public.agent_installations;
create policy agent_installations_read_member
on public.agent_installations
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists agent_installations_manage_admin on public.agent_installations;
create policy agent_installations_manage_admin
on public.agent_installations
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

drop policy if exists telemetry_policies_read_member on public.telemetry_policies;
create policy telemetry_policies_read_member
on public.telemetry_policies
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists telemetry_policies_manage_admin on public.telemetry_policies;
create policy telemetry_policies_manage_admin
on public.telemetry_policies
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

drop policy if exists feature_flags_read_member on public.feature_flags;
create policy feature_flags_read_member
on public.feature_flags
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists feature_flags_manage_admin on public.feature_flags;
create policy feature_flags_manage_admin
on public.feature_flags
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

drop policy if exists audit_logs_read_member on public.audit_logs;
create policy audit_logs_read_member
on public.audit_logs
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists tenant_usage_read_member on public.tenant_usage;
create policy tenant_usage_read_member
on public.tenant_usage
for select
to authenticated
using (public.is_tenant_member(tenant_id));

drop policy if exists tenant_usage_manage_admin on public.tenant_usage;
create policy tenant_usage_manage_admin
on public.tenant_usage
for all
to authenticated
using (public.can_manage_tenant(tenant_id))
with check (public.can_manage_tenant(tenant_id));

