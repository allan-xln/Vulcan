-- Make agent event ingestion idempotent.
--
-- Agents retry queued events when the network or API times out. Without an
-- idempotency key, a successful database commit followed by a lost HTTP
-- response can duplicate activity_events and derived metrics. The agent eventId
-- now maps to source_event_id and is unique per tenant.

alter table public.activity_events add column if not exists source_event_id text;

create unique index if not exists idx_activity_events_tenant_source_event
  on public.activity_events (tenant_id, source_event_id)
  where source_event_id is not null;
