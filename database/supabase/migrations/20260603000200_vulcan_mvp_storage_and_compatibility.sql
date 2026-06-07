alter table public.tenants add column if not exists plan text not null default 'growth';
alter table public.tenants add column if not exists region text not null default 'global';

alter table public.audit_logs add column if not exists resource_type text;
alter table public.audit_logs add column if not exists resource_id uuid;
alter table public.audit_logs add column if not exists metadata jsonb not null default '{}'::jsonb;

update public.audit_logs
set resource_type = coalesce(resource_type, entity_table, 'unknown')
where resource_type is null;

update public.audit_logs
set resource_id = coalesce(resource_id, entity_id)
where resource_id is null;

update public.audit_logs
set metadata = coalesce(metadata, change_summary, '{}'::jsonb)
where metadata = '{}'::jsonb and change_summary is not null;

create or replace function public.vulcan_storage_tenant_id(object_name text)
returns uuid
language plpgsql
immutable
as $$
begin
  return ((storage.foldername(object_name))[1])::uuid;
exception
  when others then
    return null;
end;
$$;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('tenant-assets', 'tenant-assets', false, 52428800, null),
  ('user-avatars', 'user-avatars', true, 10485760, array['image/png', 'image/jpeg', 'image/webp', 'image/svg+xml']),
  ('reports', 'reports', false, 104857600, array['application/pdf', 'text/csv', 'application/json']),
  ('exports', 'exports', false, 104857600, array['application/pdf', 'text/csv', 'application/json']),
  ('agent-packages', 'agent-packages', false, 524288000, null)
on conflict (id) do update
set
  name = excluded.name,
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types,
  updated_at = timezone('utc', now());

-- Storage object policies are owned by Supabase Storage internals in hosted projects.
-- Buckets are provisioned here; object policies are documented in docs/SUPABASE.md.
