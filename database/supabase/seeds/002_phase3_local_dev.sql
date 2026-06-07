insert into public.ingestion_api_keys (
  id,
  tenant_id,
  name,
  key_prefix,
  key_hash,
  status,
  scopes,
  metadata
) values (
  '00000000-0000-0000-0000-000000001501',
  '00000000-0000-0000-0000-000000000301',
  'Local ingestion key',
  'local_ingest',
  encode(digest('local-ingestion-key-change-me', 'sha256'), 'hex'),
  'active',
  array['operational_events:ingest']::text[],
  '{"seeded": true}'::jsonb
)
on conflict (id) do update
set
  name = excluded.name,
  key_prefix = excluded.key_prefix,
  key_hash = excluded.key_hash,
  status = excluded.status,
  scopes = excluded.scopes,
  metadata = excluded.metadata,
  updated_at = timezone('utc', now());

