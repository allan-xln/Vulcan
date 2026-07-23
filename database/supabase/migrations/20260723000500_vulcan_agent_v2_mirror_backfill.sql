-- Correct historical compatibility mirrors created before the v2 trigger guard.
-- Rows are preserved for audit, receive the canonical origin classification and
-- are marked so timeline queries can suppress only the duplicate representation.

update public.unified_events as mirror
set data_origin = canonical.data_origin,
    extensions = mirror.extensions || jsonb_build_object(
      'compatibilityMirrorSuperseded',
      true,
      'supersededByCanonicalEventId',
      canonical.id
    )
from public.unified_events as canonical
where mirror.tenant_id = canonical.tenant_id
  and mirror.source_event_id = canonical.source_event_id
  and mirror.source = 'vulcan-agent-v2'
  and mirror.extensions ->> 'legacyActivityEvent' = 'true'
  and canonical.source = 'vulcan-agent'
  and canonical.agent_id is not null;

update public.activity_events as activity
set metadata = activity.metadata || jsonb_build_object('dataOrigin', canonical.data_origin)
from public.unified_events as canonical
where activity.tenant_id = canonical.tenant_id
  and activity.source_event_id = canonical.source_event_id
  and activity.metadata ->> 'source' = 'vulcan-agent-v2'
  and canonical.source = 'vulcan-agent';
