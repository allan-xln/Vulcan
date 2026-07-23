-- Vulcan Agent v2 writes its canonical unified_event before maintaining the
-- compatibility activity_event. The legacy mirror must therefore ignore v2 rows,
-- while continuing to normalize every legacy agent event.

drop trigger if exists trg_activity_events_unified_mirror on public.activity_events;

create trigger trg_activity_events_unified_mirror
after insert on public.activity_events
for each row
when (coalesce(new.metadata ->> 'source', '') <> 'vulcan-agent-v2')
execute function app_private.vulcan_mirror_activity_event();
