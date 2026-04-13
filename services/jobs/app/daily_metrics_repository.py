from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from app.daily_metrics_rules import (
    ApplicationUsageRecord,
    DailyUserOperationalMetric,
    IdleWindowRecord,
    SessionSliceRecord,
)

if TYPE_CHECKING:
    from psycopg import Connection


@dataclass(frozen=True)
class DailyMetricBatchResult:
    run_id: UUID
    metric_row_count: int


class DailyMetricRepository(Protocol):
    def start_run(self, tenant_id: UUID | None, metric_date: date | None) -> UUID: ...
    def fetch_session_slices(self, tenant_id: UUID | None, metric_date: date | None) -> list[SessionSliceRecord]: ...
    def fetch_idle_windows(self, tenant_id: UUID | None, metric_date: date | None) -> list[IdleWindowRecord]: ...
    def fetch_application_usage_facts(self, tenant_id: UUID | None, metric_date: date | None) -> list[ApplicationUsageRecord]: ...
    def persist_daily_metrics(self, metrics: list[DailyUserOperationalMetric]) -> int: ...
    def complete_run(self, run_id: UUID, metric_row_count: int) -> None: ...
    def fail_run(self, run_id: UUID, error_message: str) -> None: ...


class PostgresDailyMetricRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self) -> "Connection":
        from psycopg import connect
        from psycopg.rows import dict_row

        return connect(self._database_url, row_factory=dict_row)

    def start_run(self, tenant_id: UUID | None, metric_date: date | None) -> UUID:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    insert into public.daily_metric_runs (tenant_id, metric_date, run_status)
                    values (%(tenant_id)s, %(metric_date)s, 'running')
                    returning id
                    """,
                    {"tenant_id": tenant_id, "metric_date": metric_date},
                )
                row = cursor.fetchone()
        return row["id"]

    def fetch_session_slices(self, tenant_id: UUID | None, metric_date: date | None) -> list[SessionSliceRecord]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    select tenant_id, workstation_id, username, started_at, duration_seconds, is_open
                    from public.session_slices
                    where (%(tenant_id)s::uuid is null or tenant_id = %(tenant_id)s::uuid)
                      and (%(metric_date)s::date is null or started_at::date = %(metric_date)s::date)
                    """,
                    {"tenant_id": tenant_id, "metric_date": metric_date},
                )
                rows = cursor.fetchall()
        return [SessionSliceRecord(**row) for row in rows]

    def fetch_idle_windows(self, tenant_id: UUID | None, metric_date: date | None) -> list[IdleWindowRecord]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    select
                      iw.tenant_id,
                      iw.workstation_id,
                      ss.username,
                      iw.started_at,
                      iw.duration_seconds,
                      iw.is_open
                    from public.idle_windows iw
                    left join public.session_slices ss
                      on ss.tenant_id = iw.tenant_id
                     and ss.workstation_id is not distinct from iw.workstation_id
                     and ss.session_id = iw.session_id
                     and iw.started_at >= ss.started_at
                     and (ss.ended_at is null or iw.started_at <= ss.ended_at)
                    where (%(tenant_id)s::uuid is null or iw.tenant_id = %(tenant_id)s::uuid)
                      and (%(metric_date)s::date is null or iw.started_at::date = %(metric_date)s::date)
                    """,
                    {"tenant_id": tenant_id, "metric_date": metric_date},
                )
                rows = cursor.fetchall()
        return [IdleWindowRecord(**row) for row in rows]

    def fetch_application_usage_facts(self, tenant_id: UUID | None, metric_date: date | None) -> list[ApplicationUsageRecord]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    select
                      auf.tenant_id,
                      auf.workstation_id,
                      ss.username,
                      auf.started_at,
                      auf.duration_seconds,
                      auf.is_open
                    from public.application_usage_facts auf
                    left join public.session_slices ss
                      on ss.tenant_id = auf.tenant_id
                     and ss.workstation_id is not distinct from auf.workstation_id
                     and ss.session_id is not distinct from auf.session_id
                     and auf.started_at >= ss.started_at
                     and (ss.ended_at is null or auf.started_at <= ss.ended_at)
                    where (%(tenant_id)s::uuid is null or auf.tenant_id = %(tenant_id)s::uuid)
                      and (%(metric_date)s::date is null or auf.started_at::date = %(metric_date)s::date)
                    """,
                    {"tenant_id": tenant_id, "metric_date": metric_date},
                )
                rows = cursor.fetchall()
        return [
            ApplicationUsageRecord(
                tenant_id=row["tenant_id"],
                workstation_id=row["workstation_id"],
                username=row["username"],
                started_at=row["started_at"],
                duration_seconds=row["duration_seconds"],
                is_open=row["is_open"],
            )
            for row in rows
        ]

    def persist_daily_metrics(self, metrics: list[DailyUserOperationalMetric]) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                for metric in metrics:
                    cursor.execute(
                        """
                        insert into public.daily_user_operational_metrics (
                          tenant_id,
                          metric_date,
                          workstation_id,
                          username,
                          session_slice_count,
                          idle_window_count,
                          application_usage_count,
                          session_time_seconds,
                          idle_time_seconds,
                          focused_app_usage_seconds
                        )
                        values (
                          %(tenant_id)s,
                          %(metric_date)s,
                          %(workstation_id)s,
                          %(username)s,
                          %(session_slice_count)s,
                          %(idle_window_count)s,
                          %(application_usage_count)s,
                          %(session_time_seconds)s,
                          %(idle_time_seconds)s,
                          %(focused_app_usage_seconds)s
                        )
                        on conflict (tenant_id, metric_date, workstation_id, username) do update
                        set session_slice_count = excluded.session_slice_count,
                            idle_window_count = excluded.idle_window_count,
                            application_usage_count = excluded.application_usage_count,
                            session_time_seconds = excluded.session_time_seconds,
                            idle_time_seconds = excluded.idle_time_seconds,
                            focused_app_usage_seconds = excluded.focused_app_usage_seconds,
                            updated_at = timezone('utc', now())
                        """,
                        metric.__dict__,
                    )
        return len(metrics)

    def complete_run(self, run_id: UUID, metric_row_count: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    update public.daily_metric_runs
                    set run_status = 'completed',
                        completed_at = timezone('utc', now()),
                        metric_row_count = %(metric_row_count)s
                    where id = %(run_id)s
                    """,
                    {"run_id": run_id, "metric_row_count": metric_row_count},
                )

    def fail_run(self, run_id: UUID, error_message: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    update public.daily_metric_runs
                    set run_status = 'failed',
                        completed_at = timezone('utc', now()),
                        error_message = %(error_message)s
                    where id = %(run_id)s
                    """,
                    {"run_id": run_id, "error_message": error_message[:2048]},
                )
