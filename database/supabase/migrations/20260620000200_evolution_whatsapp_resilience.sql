-- Evolution/Baileys transport resilience and recipient consent.
-- Secrets and QR sessions remain outside Postgres.

alter table public.memberships
  add column if not exists whatsapp_enabled boolean not null default true,
  add column if not exists whatsapp_opt_in boolean not null default false,
  add column if not exists whatsapp_opt_in_at timestamptz,
  add column if not exists whatsapp_notification_types jsonb not null default '[]'::jsonb,
  add column if not exists quiet_hours_start time,
  add column if not exists quiet_hours_end time;

alter table public.notifications
  add column if not exists delivered_at timestamptz;

alter table public.whatsapp_delivery_queue
  add column if not exists provider_instance text,
  add column if not exists idempotency_key text,
  add column if not exists dead_letter_at timestamptz,
  add column if not exists fallback_triggered_at timestamptz;

alter table public.whatsapp_delivery_queue
  drop constraint if exists whatsapp_delivery_queue_status_check;

alter table public.whatsapp_delivery_queue
  add constraint whatsapp_delivery_queue_status_check check (
    status in (
      'pending', 'queued', 'sending', 'sent', 'delivered', 'failed',
      'mocked', 'missing_credentials', 'missing_destination', 'retrying',
      'cancelled', 'skipped', 'unknown_provider', 'disabled',
      'provider_unavailable', 'qr_required', 'rate_limited'
    )
  );

create unique index if not exists uq_whatsapp_delivery_queue_idempotency
  on public.whatsapp_delivery_queue (tenant_id, recipient_membership_id, idempotency_key)
  where idempotency_key is not null;

create index if not exists idx_whatsapp_delivery_queue_worker
  on public.whatsapp_delivery_queue (status, next_attempt_at, created_at)
  where status in ('pending', 'queued', 'retrying', 'provider_unavailable', 'qr_required', 'rate_limited');

create index if not exists idx_memberships_whatsapp_delivery
  on public.memberships (tenant_id, whatsapp_enabled, whatsapp_opt_in)
  where status = 'active' and whatsapp is not null;

update public.memberships
set whatsapp_opt_in = true,
    whatsapp_opt_in_at = coalesce(whatsapp_opt_in_at, timezone('utc', now()))
where tenant_id = '00000000-0000-0000-0000-000000000301'::uuid
  and nullif(regexp_replace(coalesce(whatsapp, ''), '\D', '', 'g'), '') is not null
  and coalesce(metadata ->> 'seed', '') = 'vulcan-demo';
