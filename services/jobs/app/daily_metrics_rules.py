from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable
from uuid import UUID


@dataclass(frozen=True)
class SessionSliceRecord:
    tenant_id: UUID
    workstation_id: UUID | None
    username: str | None
    started_at: datetime
    duration_seconds: int | None
    is_open: bool


@dataclass(frozen=True)
class IdleWindowRecord:
    tenant_id: UUID
    workstation_id: UUID | None
    username: str | None
    started_at: datetime
    duration_seconds: int | None
    is_open: bool


@dataclass(frozen=True)
class ApplicationUsageRecord:
    tenant_id: UUID
    workstation_id: UUID | None
    username: str | None
    started_at: datetime
    duration_seconds: int | None
    is_open: bool


@dataclass(frozen=True)
class DailyUserOperationalMetric:
    tenant_id: UUID
    metric_date: date
    workstation_id: UUID | None
    username: str | None
    session_slice_count: int
    idle_window_count: int
    application_usage_count: int
    session_time_seconds: int
    idle_time_seconds: int
    focused_app_usage_seconds: int


def derive_daily_user_operational_metrics(
    session_slices: Iterable[SessionSliceRecord],
    idle_windows: Iterable[IdleWindowRecord],
    application_usage_facts: Iterable[ApplicationUsageRecord],
) -> list[DailyUserOperationalMetric]:
    buckets: dict[tuple[UUID, date, UUID | None, str | None], dict[str, int]] = {}

    for slice_record in session_slices:
        if slice_record.is_open or slice_record.duration_seconds is None:
            continue
        key = (
            slice_record.tenant_id,
            slice_record.started_at.date(),
            slice_record.workstation_id,
            slice_record.username,
        )
        bucket = buckets.setdefault(
            key,
            {
                "session_slice_count": 0,
                "idle_window_count": 0,
                "application_usage_count": 0,
                "session_time_seconds": 0,
                "idle_time_seconds": 0,
                "focused_app_usage_seconds": 0,
            },
        )
        bucket["session_slice_count"] += 1
        bucket["session_time_seconds"] += slice_record.duration_seconds

    for idle_record in idle_windows:
        if idle_record.is_open or idle_record.duration_seconds is None:
            continue
        key = (
            idle_record.tenant_id,
            idle_record.started_at.date(),
            idle_record.workstation_id,
            idle_record.username,
        )
        bucket = buckets.setdefault(
            key,
            {
                "session_slice_count": 0,
                "idle_window_count": 0,
                "application_usage_count": 0,
                "session_time_seconds": 0,
                "idle_time_seconds": 0,
                "focused_app_usage_seconds": 0,
            },
        )
        bucket["idle_window_count"] += 1
        bucket["idle_time_seconds"] += idle_record.duration_seconds

    for app_record in application_usage_facts:
        if app_record.is_open or app_record.duration_seconds is None:
            continue
        key = (
            app_record.tenant_id,
            app_record.started_at.date(),
            app_record.workstation_id,
            app_record.username,
        )
        bucket = buckets.setdefault(
            key,
            {
                "session_slice_count": 0,
                "idle_window_count": 0,
                "application_usage_count": 0,
                "session_time_seconds": 0,
                "idle_time_seconds": 0,
                "focused_app_usage_seconds": 0,
            },
        )
        bucket["application_usage_count"] += 1
        bucket["focused_app_usage_seconds"] += app_record.duration_seconds

    return [
        DailyUserOperationalMetric(
            tenant_id=tenant_id,
            metric_date=metric_date,
            workstation_id=workstation_id,
            username=username,
            session_slice_count=values["session_slice_count"],
            idle_window_count=values["idle_window_count"],
            application_usage_count=values["application_usage_count"],
            session_time_seconds=values["session_time_seconds"],
            idle_time_seconds=values["idle_time_seconds"],
            focused_app_usage_seconds=values["focused_app_usage_seconds"],
        )
        for (tenant_id, metric_date, workstation_id, username), values in sorted(buckets.items())
    ]
