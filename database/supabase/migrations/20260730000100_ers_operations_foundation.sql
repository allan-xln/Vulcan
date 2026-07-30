-- Vulcan ERS operational closeout foundation.
-- Additive and idempotent: preserves the existing Workforce, sites and asset records.

alter table public.sites
  add column if not exists slug text,
  add column if not exists city text,
  add column if not exists state text,
  add column if not exists display_order integer not null default 0,
  add column if not exists semantic_color text,
  add column if not exists latitude numeric(10, 7),
  add column if not exists longitude numeric(10, 7),
  add column if not exists rotation_enabled boolean not null default true,
  add column if not exists rotation_seconds integer not null default 30,
  add column if not exists visible boolean not null default true,
  add column if not exists source text not null default 'manual';

update public.sites
set slug = lower(regexp_replace(btrim(code), '[^a-zA-Z0-9]+', '-', 'g'))
where slug is null or btrim(slug) = '';

alter table public.sites
  alter column slug set not null;

alter table public.sites
  drop constraint if exists sites_rotation_seconds_check;
alter table public.sites
  add constraint sites_rotation_seconds_check check (rotation_seconds between 10 and 3600);

create unique index if not exists idx_sites_tenant_slug
  on public.sites (tenant_id, lower(slug));
create index if not exists idx_sites_tenant_display
  on public.sites (tenant_id, visible, display_order, name);

alter table public.infrastructure_networks
  add column if not exists source text not null default 'manual',
  add column if not exists source_key text;

create unique index if not exists idx_infrastructure_networks_source_key
  on public.infrastructure_networks (tenant_id, source, source_key)
  where source_key is not null and btrim(source_key) <> '';

alter table public.infrastructure_assets
  add column if not exists source_key text;

alter table public.infrastructure_assets
  drop constraint if exists infrastructure_assets_asset_type_check;
alter table public.infrastructure_assets
  add constraint infrastructure_assets_asset_type_check check (
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
      'proxmox_cluster',
      'virtualization_host',
      'backup_server',
      'backup_job',
      'wan_link',
      'vpn_tunnel',
      'nat_service',
      'network_service',
      'other'
    )
  );

create unique index if not exists idx_infrastructure_assets_source_key
  on public.infrastructure_assets (tenant_id, source, source_key)
  where source_key is not null and btrim(source_key) <> '';

create table if not exists public.wallboard_profiles (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  site_id uuid,
  slug text not null,
  name text not null,
  wallboard_type text not null check (wallboard_type in ('workforce', 'infrastructure')),
  view_mode text not null default 'overview',
  enabled boolean not null default true,
  refresh_seconds integer not null default 30 check (refresh_seconds between 5 and 3600),
  fullscreen boolean not null default true,
  night_mode boolean not null default true,
  burn_in_prevention boolean not null default true,
  show_clock boolean not null default true,
  show_last_update boolean not null default true,
  show_connection_status boolean not null default true,
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, slug),
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete set null
);

create table if not exists public.wallboard_playlists (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  profile_id uuid not null,
  slug text not null,
  name text not null,
  enabled boolean not null default true,
  rotation_enabled boolean not null default true,
  default_duration_seconds integer not null default 30 check (default_duration_seconds between 10 and 3600),
  transition text not null default 'none' check (transition in ('none', 'fade', 'slide')),
  schedule jsonb not null default '{}'::jsonb,
  alert_priority_enabled boolean not null default true,
  auto_return_seconds integer not null default 120 check (auto_return_seconds between 10 and 86400),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, slug),
  foreign key (tenant_id, profile_id) references public.wallboard_profiles (tenant_id, id) on delete cascade
);

create table if not exists public.wallboard_playlist_items (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  playlist_id uuid not null,
  site_id uuid,
  panel_key text not null,
  title text not null,
  position integer not null check (position >= 0),
  duration_seconds integer check (duration_seconds is null or duration_seconds between 10 and 3600),
  enabled boolean not null default true,
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, playlist_id, position),
  foreign key (tenant_id, playlist_id) references public.wallboard_playlists (tenant_id, id) on delete cascade,
  foreign key (tenant_id, site_id) references public.sites (tenant_id, id) on delete set null
);

create table if not exists public.wallboard_devices (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  profile_id uuid,
  playlist_id uuid,
  name text not null,
  device_fingerprint text not null,
  status text not null default 'pending' check (status in ('pending', 'active', 'offline', 'revoked')),
  token_fingerprint text,
  last_seen_at timestamptz,
  last_ip inet,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  unique (tenant_id, device_fingerprint),
  foreign key (tenant_id, profile_id) references public.wallboard_profiles (tenant_id, id) on delete set null,
  foreign key (tenant_id, playlist_id) references public.wallboard_playlists (tenant_id, id) on delete set null
);

create table if not exists public.wallboard_sessions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.tenants (id) on delete cascade,
  device_id uuid,
  profile_id uuid not null,
  playlist_id uuid,
  session_key_hash text not null,
  status text not null default 'active' check (status in ('active', 'expired', 'revoked')),
  current_item_id uuid,
  connected_at timestamptz not null default timezone('utc', now()),
  last_seen_at timestamptz not null default timezone('utc', now()),
  expires_at timestamptz not null,
  revoked_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  unique (tenant_id, id),
  foreign key (tenant_id, device_id) references public.wallboard_devices (tenant_id, id) on delete set null,
  foreign key (tenant_id, profile_id) references public.wallboard_profiles (tenant_id, id) on delete cascade,
  foreign key (tenant_id, playlist_id) references public.wallboard_playlists (tenant_id, id) on delete set null,
  foreign key (tenant_id, current_item_id) references public.wallboard_playlist_items (tenant_id, id) on delete set null,
  check (expires_at > connected_at)
);

create index if not exists idx_wallboard_profiles_tenant
  on public.wallboard_profiles (tenant_id, enabled, wallboard_type, name);
create index if not exists idx_wallboard_playlists_profile
  on public.wallboard_playlists (tenant_id, profile_id, enabled);
create index if not exists idx_wallboard_playlist_items_order
  on public.wallboard_playlist_items (tenant_id, playlist_id, enabled, position);
create index if not exists idx_wallboard_devices_status
  on public.wallboard_devices (tenant_id, status, last_seen_at desc);
create index if not exists idx_wallboard_sessions_active
  on public.wallboard_sessions (tenant_id, status, expires_at)
  where status = 'active';

drop trigger if exists trg_wallboard_profiles_updated_at on public.wallboard_profiles;
create trigger trg_wallboard_profiles_updated_at before update on public.wallboard_profiles
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_wallboard_playlists_updated_at on public.wallboard_playlists;
create trigger trg_wallboard_playlists_updated_at before update on public.wallboard_playlists
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_wallboard_playlist_items_updated_at on public.wallboard_playlist_items;
create trigger trg_wallboard_playlist_items_updated_at before update on public.wallboard_playlist_items
for each row execute function app_private.vulcan_set_updated_at();
drop trigger if exists trg_wallboard_devices_updated_at on public.wallboard_devices;
create trigger trg_wallboard_devices_updated_at before update on public.wallboard_devices
for each row execute function app_private.vulcan_set_updated_at();

alter table public.wallboard_profiles enable row level security;
alter table public.wallboard_playlists enable row level security;
alter table public.wallboard_playlist_items enable row level security;
alter table public.wallboard_devices enable row level security;
alter table public.wallboard_sessions enable row level security;

drop policy if exists wallboard_profiles_read_member on public.wallboard_profiles;
create policy wallboard_profiles_read_member on public.wallboard_profiles
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists wallboard_profiles_manage_admin on public.wallboard_profiles;
create policy wallboard_profiles_manage_admin on public.wallboard_profiles
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists wallboard_playlists_read_member on public.wallboard_playlists;
create policy wallboard_playlists_read_member on public.wallboard_playlists
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists wallboard_playlists_manage_admin on public.wallboard_playlists;
create policy wallboard_playlists_manage_admin on public.wallboard_playlists
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists wallboard_playlist_items_read_member on public.wallboard_playlist_items;
create policy wallboard_playlist_items_read_member on public.wallboard_playlist_items
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists wallboard_playlist_items_manage_admin on public.wallboard_playlist_items;
create policy wallboard_playlist_items_manage_admin on public.wallboard_playlist_items
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists wallboard_devices_read_member on public.wallboard_devices;
create policy wallboard_devices_read_member on public.wallboard_devices
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists wallboard_devices_manage_admin on public.wallboard_devices;
create policy wallboard_devices_manage_admin on public.wallboard_devices
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists wallboard_sessions_read_member on public.wallboard_sessions;
create policy wallboard_sessions_read_member on public.wallboard_sessions
for select to authenticated using (public.vulcan_is_tenant_member(tenant_id));
drop policy if exists wallboard_sessions_manage_admin on public.wallboard_sessions;
create policy wallboard_sessions_manage_admin on public.wallboard_sessions
for all to authenticated using (public.vulcan_has_tenant_scope(tenant_id))
with check (public.vulcan_has_tenant_scope(tenant_id));

drop policy if exists service_role_all_wallboard_profiles on public.wallboard_profiles;
create policy service_role_all_wallboard_profiles on public.wallboard_profiles
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_wallboard_playlists on public.wallboard_playlists;
create policy service_role_all_wallboard_playlists on public.wallboard_playlists
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_wallboard_playlist_items on public.wallboard_playlist_items;
create policy service_role_all_wallboard_playlist_items on public.wallboard_playlist_items
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_wallboard_devices on public.wallboard_devices;
create policy service_role_all_wallboard_devices on public.wallboard_devices
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
drop policy if exists service_role_all_wallboard_sessions on public.wallboard_sessions;
create policy service_role_all_wallboard_sessions on public.wallboard_sessions
for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');

grant select on public.wallboard_profiles, public.wallboard_playlists,
  public.wallboard_playlist_items, public.wallboard_devices, public.wallboard_sessions
to authenticated;
grant insert, update, delete on public.wallboard_profiles, public.wallboard_playlists,
  public.wallboard_playlist_items, public.wallboard_devices, public.wallboard_sessions
to authenticated;
grant all privileges on public.wallboard_profiles, public.wallboard_playlists,
  public.wallboard_playlist_items, public.wallboard_devices, public.wallboard_sessions
to service_role;
