-- Production access foundation for the on-premises Vulcan release.
-- Additive: existing module rows, tenant data and Supabase authentication remain valid.

alter table public.tenant_modules
  drop constraint if exists tenant_modules_module_key_check;

alter table public.tenant_modules
  add constraint tenant_modules_module_key_check
  check (
    module_key in (
      'workforce',
      'infrastructure',
      'timeline',
      'assets',
      'agents',
      'print',
      'security',
      'intelligence',
      'wallboard',
      'automations',
      'compliance',
      'administration'
    )
  );

insert into public.tenant_modules (tenant_id, module_key, enabled, plan_source, enabled_at)
select tenant.id, module.module_key, false, 'tenant', null
from public.tenants tenant
cross join (values ('agents'), ('wallboard')) as module(module_key)
on conflict (tenant_id, module_key) do nothing;
