from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


SchemaVersion = Literal["2026-04-telemetry.v1"]
TelemetryEventType = Literal[
    "heartbeat",
    "session_lock",
    "session_unlock",
    "session_login",
    "session_logout",
    "idle_start",
    "idle_end",
    "foreground_application_change",
    "process_start",
    "process_stop",
]


class SourceContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workstation_id: UUID = Field(alias="workstationId")
    agent_installation_id: UUID | None = Field(default=None, alias="agentInstallationId")
    agent_version: str | None = Field(default=None, alias="agentVersion", max_length=64)


class HeartbeatPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["online"]
    queue_depth: int = Field(alias="queueDepth", ge=0)


class SessionBoundaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: Annotated[str, StringConstraints(min_length=1, max_length=128)] = Field(alias="sessionId")
    username: str | None = Field(default=None, max_length=128)


class IdlePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: Annotated[str, StringConstraints(min_length=1, max_length=128)] = Field(alias="sessionId")
    idle_threshold_seconds: int = Field(alias="idleThresholdSeconds", ge=1, le=86400)


class ForegroundApplicationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str | None = Field(default=None, alias="sessionId", max_length=128)
    app_name: Annotated[str, StringConstraints(min_length=1, max_length=255)] = Field(alias="appName")
    executable_path: str | None = Field(default=None, alias="executablePath", max_length=1024)
    window_title: str | None = Field(default=None, alias="windowTitle", max_length=1024)


class ProcessPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_name: Annotated[str, StringConstraints(min_length=1, max_length=255)] = Field(alias="processName")
    executable_path: str | None = Field(default=None, alias="executablePath", max_length=1024)
    pid: int | None = Field(default=None, ge=0)


class EventBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(alias="eventId")
    occurred_at: datetime = Field(alias="occurredAt")
    source: SourceContext


class HeartbeatEvent(EventBase):
    event_type: Literal["heartbeat"] = Field(alias="eventType")
    payload: HeartbeatPayload


class SessionBoundaryEvent(EventBase):
    event_type: Literal["session_lock", "session_unlock", "session_login", "session_logout"] = Field(alias="eventType")
    payload: SessionBoundaryPayload


class IdleEvent(EventBase):
    event_type: Literal["idle_start", "idle_end"] = Field(alias="eventType")
    payload: IdlePayload


class ForegroundApplicationChangeEvent(EventBase):
    event_type: Literal["foreground_application_change"] = Field(alias="eventType")
    payload: ForegroundApplicationPayload


class ProcessEvent(EventBase):
    event_type: Literal["process_start", "process_stop"] = Field(alias="eventType")
    payload: ProcessPayload


TelemetryEvent = Annotated[
    Union[
        HeartbeatEvent,
        SessionBoundaryEvent,
        IdleEvent,
        ForegroundApplicationChangeEvent,
        ProcessEvent,
    ],
    Field(discriminator="event_type"),
]


class TelemetryBatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: SchemaVersion = Field(alias="schemaVersion")
    batch_id: str | None = Field(default=None, alias="batchId", min_length=1, max_length=128)
    sent_at: datetime = Field(alias="sentAt")
    events: list[TelemetryEvent] = Field(min_length=1, max_length=500)


class AcceptedEvent(BaseModel):
    source_event_id: UUID = Field(alias="sourceEventId")
    ingestion_status: Literal["accepted", "duplicate"] = Field(alias="ingestionStatus")
    raw_event_id: UUID = Field(alias="rawEventId")


class TelemetryBatchResponse(BaseModel):
    request_id: UUID = Field(alias="requestId")
    tenant_id: UUID = Field(alias="tenantId")
    accepted_count: int = Field(alias="acceptedCount")
    duplicate_count: int = Field(alias="duplicateCount")
    results: list[AcceptedEvent]
