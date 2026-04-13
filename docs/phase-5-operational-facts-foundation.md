# Phase 5 Operational Facts Foundation

## Goal
Derive deterministic session slices, idle windows and application usage facts from normalized operational events.

## Explicit transformation rules
- Session slices start on `session_login` or `session_unlock`.
- Session slices end on `session_lock` or `session_logout`.
- If a new session start appears before a previous session closes, the previous slice closes with `superseded_by_new_session_start`.
- Idle windows start on `idle_start`.
- Idle windows end on `idle_end` or on session end if no explicit idle end appears first.
- Application usage facts start on `foreground_application_change`.
- Application usage facts end on the next `foreground_application_change`, `idle_start`, `session_lock`, or `session_logout`.
- Every fact is keyed by its start normalized event id, so reruns update the same fact instead of duplicating it.

## Replay safety
- Facts are upserted by stable natural keys:
  - `session_slices.start_normalized_event_id`
  - `idle_windows.start_normalized_event_id`
  - `application_usage_facts.focus_start_normalized_event_id`
- Rerunning the job is deterministic and does not create duplicates.

## Out of scope in this phase
- team rollups
- daily metrics
- anomaly detection
- scoring
- dashboards
- explainable AI

