-- Preserve identity history while enforcing exactly one active identity for a
-- tenant/device fingerprint. Secure re-enrollment revokes the previous identity
-- in the same transaction before inserting its replacement.

alter table public.agent_identities
  drop constraint if exists agent_identities_tenant_id_device_fingerprint_key;

create unique index if not exists uq_agent_identities_active_device_fingerprint
  on public.agent_identities (tenant_id, device_fingerprint)
  where status not in ('revoked', 'retired');
