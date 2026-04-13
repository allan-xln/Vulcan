from __future__ import annotations

from datetime import date, datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class PaginationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class BaseFilterParams(PaginationParams):
    tenant_id: UUID = Field(alias="tenantId")
    date_from: date | None = Field(default=None, alias="dateFrom")
    date_to: date | None = Field(default=None, alias="dateTo")
    workstation_id: UUID | None = Field(default=None, alias="workstationId")
    username: str | None = None


class DailyMetricItem(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    metric_date: date = Field(alias="metricDate")
    workstation_id: UUID | None = Field(alias="workstationId")
    username: str | None
    session_slice_count: int = Field(alias="sessionSliceCount")
    idle_window_count: int = Field(alias="idleWindowCount")
    application_usage_count: int = Field(alias="applicationUsageCount")
    session_time_seconds: int = Field(alias="sessionTimeSeconds")
    idle_time_seconds: int = Field(alias="idleTimeSeconds")
    focused_app_usage_seconds: int = Field(alias="focusedAppUsageSeconds")


class SessionSliceItem(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    workstation_id: UUID | None = Field(alias="workstationId")
    session_id: str = Field(alias="sessionId")
    username: str | None
    started_at: datetime = Field(alias="startedAt")
    ended_at: datetime | None = Field(alias="endedAt")
    duration_seconds: int | None = Field(alias="durationSeconds")
    start_event_type: str = Field(alias="startEventType")
    end_event_type: str | None = Field(alias="endEventType")
    closure_reason: str = Field(alias="closureReason")
    is_open: bool = Field(alias="isOpen")


class IdleWindowItem(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    workstation_id: UUID | None = Field(alias="workstationId")
    session_id: str = Field(alias="sessionId")
    started_at: datetime = Field(alias="startedAt")
    ended_at: datetime | None = Field(alias="endedAt")
    duration_seconds: int | None = Field(alias="durationSeconds")
    idle_threshold_seconds: int | None = Field(alias="idleThresholdSeconds")
    closure_reason: str = Field(alias="closureReason")
    is_open: bool = Field(alias="isOpen")


class ApplicationUsageItem(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    workstation_id: UUID | None = Field(alias="workstationId")
    session_id: str | None = Field(alias="sessionId")
    app_name: str = Field(alias="appName")
    process_name: str | None = Field(alias="processName")
    started_at: datetime = Field(alias="startedAt")
    ended_at: datetime | None = Field(alias="endedAt")
    duration_seconds: int | None = Field(alias="durationSeconds")
    end_reason: str = Field(alias="endReason")
    is_open: bool = Field(alias="isOpen")


class PaginatedResponse(ApiModel, Generic[T]):
    total: int
    limit: int
    offset: int
    items: list[T]


class HealthResponse(ApiModel):
    status: str
    service: str
    data_boundary: str
