# Phase 6 Daily Metrics Foundation

## Goal
Derive deterministic daily user-level operational metrics from session slices, idle windows and application usage facts.

## Explicit formulas
- `session_slice_count = count(session_slices fechadas iniciadas no dia)`
- `session_time_seconds = sum(session_slices.duration_seconds fechadas iniciadas no dia)`
- `idle_window_count = count(idle_windows fechadas iniciadas no dia)`
- `idle_time_seconds = sum(idle_windows.duration_seconds fechadas iniciadas no dia)`
- `application_usage_count = count(application_usage_facts fechadas iniciadas no dia)`
- `focused_app_usage_seconds = sum(application_usage_facts.duration_seconds fechadas iniciadas no dia)`

## Notes
- Open facts are intentionally excluded from the daily metrics base.
- Idle metrics are currently aggregated at `tenant + date + workstation` with `username = null`, because Phase 5 facts do not yet attribute idle windows to a user identity beyond session context.
- The aggregation key is `tenant_id + metric_date + workstation_id + username`.

## Out of scope in this phase
- team rollups
- dashboard APIs
- anomaly detection
- scores
- AI explanations

