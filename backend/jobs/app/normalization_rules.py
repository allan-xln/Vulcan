from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class RawOperationalEventRecord:
    raw_event_id: UUID
    tenant_id: UUID
    source_event_id: UUID
    workstation_id: UUID | None
    agent_installation_id: UUID | None
    schema_version: str
    event_type: str
    occurred_at: datetime
    received_at: datetime
    event_payload: dict[str, Any]


@dataclass(frozen=True)
class NormalizedOperationalEvent:
    raw_event_id: UUID
    tenant_id: UUID
    source_event_id: UUID
    workstation_id: UUID | None
    agent_installation_id: UUID | None
    normalized_event_type: str
    schema_version: str
    occurred_at: datetime
    received_at: datetime
    session_id: str | None
    username: str | None
    app_name: str | None
    process_name: str | None
    queue_depth: int | None
    idle_threshold_seconds: int | None
    normalized_payload: dict[str, Any]


def normalize_raw_event(raw_event: RawOperationalEventRecord) -> NormalizedOperationalEvent:
    payload = raw_event.event_payload.get("payload", {})

    session_id = payload.get("sessionId")
    username = payload.get("username")
    app_name = payload.get("appName")
    process_name = payload.get("processName")
    queue_depth = payload.get("queueDepth")
    idle_threshold_seconds = payload.get("idleThresholdSeconds")

    normalized_payload = {
      "source": raw_event.event_payload.get("source", {}),
      "payload": payload,
    }

    return NormalizedOperationalEvent(
        raw_event_id=raw_event.raw_event_id,
        tenant_id=raw_event.tenant_id,
        source_event_id=raw_event.source_event_id,
        workstation_id=raw_event.workstation_id,
        agent_installation_id=raw_event.agent_installation_id,
        normalized_event_type=raw_event.event_type,
        schema_version=raw_event.schema_version,
        occurred_at=raw_event.occurred_at,
        received_at=raw_event.received_at,
        session_id=session_id,
        username=username,
        app_name=app_name,
        process_name=process_name,
        queue_depth=queue_depth,
        idle_threshold_seconds=idle_threshold_seconds,
        normalized_payload=normalized_payload,
    )

