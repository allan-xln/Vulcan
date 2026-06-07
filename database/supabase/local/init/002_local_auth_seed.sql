insert into auth.users (
  id,
  email,
  raw_user_meta_data
) values (
  '11111111-1111-1111-1111-111111111111',
  'owner@local.test',
  '{"full_name": "Local Owner"}'::jsonb
)
on conflict (id) do update
set
  email = excluded.email,
  raw_user_meta_data = excluded.raw_user_meta_data,
  updated_at = timezone('utc', now());

