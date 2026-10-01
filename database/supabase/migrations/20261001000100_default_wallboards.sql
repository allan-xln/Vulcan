insert into public.wallboard_profiles (
  tenant_id,
  slug,
  name,
  wallboard_type,
  view_mode,
  enabled,
  refresh_seconds,
  fullscreen,
  night_mode,
  burn_in_prevention,
  show_clock,
  show_last_update,
  show_connection_status,
  config
)
select
  tenant.id,
  profile.slug,
  profile.name,
  profile.wallboard_type,
  'overview',
  true,
  30,
  true,
  true,
  true,
  true,
  true,
  true,
  profile.config
from public.tenants tenant
cross join (
  values
    (
      'vulcan-workforce',
      'Vulcan Operação',
      'workforce',
      '{"privacyMode":"aggregate","sceneSequence":["command","economy","pulse","teams","applications","branches","collection"]}'::jsonb
    ),
    (
      'vulcan-infrastructure',
      'Vulcan Infraestrutura',
      'infrastructure',
      '{"privacyMode":"aggregate","sceneSequence":["command","topology","connectivity","proxmox","servers","unifi","printing","platform"]}'::jsonb
    )
) as profile(slug, name, wallboard_type, config)
where tenant.status = 'active'
on conflict (tenant_id, slug) do update
set name = excluded.name,
    wallboard_type = excluded.wallboard_type,
    enabled = true,
    config = coalesce(public.wallboard_profiles.config, '{}'::jsonb) || excluded.config,
    updated_at = timezone('utc', now());

insert into public.wallboard_playlists (
  tenant_id,
  profile_id,
  slug,
  name,
  enabled,
  rotation_enabled,
  default_duration_seconds,
  transition,
  alert_priority_enabled,
  auto_return_seconds
)
select
  profile.tenant_id,
  profile.id,
  profile.slug || '-principal',
  'Rotação principal',
  true,
  true,
  30,
  'fade',
  true,
  120
from public.wallboard_profiles profile
where profile.slug in ('vulcan-workforce', 'vulcan-infrastructure')
on conflict (tenant_id, slug) do update
set profile_id = excluded.profile_id,
    enabled = true,
    rotation_enabled = true,
    transition = excluded.transition,
    updated_at = timezone('utc', now());

insert into public.wallboard_playlist_items (
  tenant_id,
  playlist_id,
  panel_key,
  title,
  position,
  duration_seconds,
  enabled
)
select
  playlist.tenant_id,
  playlist.id,
  'overview',
  case
    when profile.wallboard_type = 'workforce' then 'Operação ERS'
    else 'Infraestrutura ERS'
  end,
  0,
  30,
  true
from public.wallboard_playlists playlist
join public.wallboard_profiles profile
  on profile.tenant_id = playlist.tenant_id
 and profile.id = playlist.profile_id
where profile.slug in ('vulcan-workforce', 'vulcan-infrastructure')
on conflict (tenant_id, playlist_id, position) do update
set panel_key = excluded.panel_key,
    title = excluded.title,
    duration_seconds = excluded.duration_seconds,
    enabled = true,
    updated_at = timezone('utc', now());
