# Phase 4 Normalization Foundation

## Goal
Transform accepted raw telemetry intake into deterministic normalized operational events ready for later analytics.

## Explicit transformation rules
- `normalized_event_type` is copied directly from the accepted raw `event_type`.
- `raw_operational_event_intake_id` is the immutable lineage pointer for every normalized fact.
- `schema_version`, `occurred_at`, `received_at`, `tenant_id`, `workstation_id` and `agent_installation_id` are copied directly from raw intake.
- `session_id` is extracted only from payloads that explicitly contain `sessionId`.
- `username` is extracted only from payloads that explicitly contain `username`.
- `app_name` is extracted only from payloads that explicitly contain `appName`.
- `process_name` is extracted only from payloads that explicitly contain `processName`.
- `queue_depth` is extracted only from heartbeat payloads that explicitly contain `queueDepth`.
- `idle_threshold_seconds` is extracted only from idle payloads that explicitly contain `idleThresholdSeconds`.
- `normalized_payload` stores the original raw `source` and raw `payload` sections without inference.

## Replay safety
- the job fetches only accepted raw rows not yet present in `normalized_operational_events`
- inserts use unique `raw_operational_event_intake_id`
- rerunning the job is safe and deterministic

## Out of scope in this phase
- session slicing
- app usage rollups
- anomaly detection
- ClickHouse persistence
- dashboards

