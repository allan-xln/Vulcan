from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from app.fact_rules import (
    ApplicationUsageFact,
    IdleWindowFact,
    NormalizedEventRecord,
    SessionSliceFact,
)

if TYPE_CHECKING:
    from psycopg import Connection


@dataclass(frozen=True)
class OperationalFactBatchResult:
    run_id: UUID
    session_slice_count: int
    idle_window_count: int
    application_usage_count: int


class OperationalFactRepository(Protocol):
    def start_run(self, tenant_id: UUID | None) -> UUID: ...
    def fetch_normalized_events(self, tenant_id: UUID | None) -> list[NormalizedEventRecord]: ...
    def persist_session_slices(self, facts: list[SessionSliceFact]) -> int: ...
    def persist_idle_windows(self, facts: list[IdleWindowFact]) -> int: ...
    def persist_application_usage_facts(self, facts: list[ApplicationUsageFact]) -> int: ...
    def complete_run(self, run_id: UUID, session_slice_count: int, idle_window_count: int, application_usage_count: int) -> None: ...
    def fail_run(self, run_id: UUID, error_message: str) -> None: ...


class PostgresOperationalFactRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self) -> "Connection":
        from psycopg import connect
        from psycopg.rows import dict_row

        return connect(self._database_url, row_factory=dict_row)

    def start_run(self, tenant_id: UUID | None) -> UUID:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    insert into public.operational_fact_runs (tenant_id, run_status)
                    values (%(tenant_id)s, 'running')
                    returning id
                    """,
                    {"tenant_id": tenant_id},
                )
                row = cursor.fetchone()
        return row["id"]

    def fetch_normalized_events(self, tenant_id: UUID | None) -> list[NormalizedEventRecord]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    select
                      id as normalized_event_id,
                      tenant_id,
                      workstation_id,
                      agent_installation_id,
                      normalized_event_type,
                      occurred_at,
                      session_id,
                      username,
                      app_name,
                      process_name,
                      idle_threshold_seconds
                    from public.normalized_operational_events
                    where (%(tenant_id)s::uuid is null or tenant_id = %(tenant_id)s::uuid)
                    order by tenant_id, workstation_id nulls first, session_id nulls first, occurred_at, id
                    """,
                    {"tenant_id": tenant_id},
                )
                rows = cursor.fetchall()

        return [
            NormalizedEventRecord(
                normalized_event_id=row["normalized_event_id"],
                tenant_id=row["tenant_id"],
                workstation_id=row["workstation_id"],
                agent_installation_id=row["agent_installation_id"],
                normalized_event_type=row["normalized_event_type"],
                occurred_at=row["occurred_at"],
                session_id=row["session_id"],
                username=row["username"],
                app_name=row["app_name"],
                process_name=row["process_name"],
                idle_threshold_seconds=row["idle_threshold_seconds"],
            )
            for row in rows
        ]

    def persist_session_slices(self, facts: list[SessionSliceFact]) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                for fact in facts:
                    cursor.execute(
                        """
                        insert into public.session_slices (
                          tenant_id,
                          workstation_id,
                          agent_installation_id,
                          session_id,
                          username,
                          start_normalized_event_id,
                          end_normalized_event_id,
                          started_at,
                          ended_at,
                          duration_seconds,
                          start_event_type,
                          end_event_type,
                          closure_reason,
                          is_open
                        )
                        values (
                          %(tenant_id)s,
                          %(workstation_id)s,
                          %(agent_installation_id)s,
                          %(session_id)s,
                          %(username)s,
                          %(start_normalized_event_id)s,
                          %(end_normalized_event_id)s,
                          %(started_at)s,
                          %(ended_at)s,
                          %(duration_seconds)s,
                          %(start_event_type)s,
                          %(end_event_type)s,
                          %(closure_reason)s,
                          %(is_open)s
                        )
                        on conflict (start_normalized_event_id) do update
                        set end_normalized_event_id = excluded.end_normalized_event_id,
                            ended_at = excluded.ended_at,
                            duration_seconds = excluded.duration_seconds,
                            end_event_type = excluded.end_event_type,
                            closure_reason = excluded.closure_reason,
                            is_open = excluded.is_open,
                            updated_at = timezone('utc', now())
                        """,
                        fact.__dict__,
                    )
        return len(facts)

    def persist_idle_windows(self, facts: list[IdleWindowFact]) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                for fact in facts:
                    cursor.execute(
                        """
                        insert into public.idle_windows (
                          tenant_id,
                          workstation_id,
                          agent_installation_id,
                          session_id,
                          start_normalized_event_id,
                          end_normalized_event_id,
                          started_at,
                          ended_at,
                          duration_seconds,
                          idle_threshold_seconds,
                          closure_reason,
                          is_open
                        )
                        values (
                          %(tenant_id)s,
                          %(workstation_id)s,
                          %(agent_installation_id)s,
                          %(session_id)s,
                          %(start_normalized_event_id)s,
                          %(end_normalized_event_id)s,
                          %(started_at)s,
                          %(ended_at)s,
                          %(duration_seconds)s,
                          %(idle_threshold_seconds)s,
                          %(closure_reason)s,
                          %(is_open)s
                        )
                        on conflict (start_normalized_event_id) do update
                        set end_normalized_event_id = excluded.end_normalized_event_id,
                            ended_at = excluded.ended_at,
                            duration_seconds = excluded.duration_seconds,
                            idle_threshold_seconds = excluded.idle_threshold_seconds,
                            closure_reason = excluded.closure_reason,
                            is_open = excluded.is_open,
                            updated_at = timezone('utc', now())
                        """,
                        fact.__dict__,
                    )
        return len(facts)

    def persist_application_usage_facts(self, facts: list[ApplicationUsageFact]) -> int:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                for fact in facts:
                    cursor.execute(
                        """
                        insert into public.application_usage_facts (
                          tenant_id,
                          workstation_id,
                          agent_installation_id,
                          session_id,
                          app_name,
                          process_name,
                          focus_start_normalized_event_id,
                          focus_end_normalized_event_id,
                          started_at,
                          ended_at,
                          duration_seconds,
                          end_reason,
                          is_open
                        )
                        values (
                          %(tenant_id)s,
                          %(workstation_id)s,
                          %(agent_installation_id)s,
                          %(session_id)s,
                          %(app_name)s,
                          %(process_name)s,
                          %(focus_start_normalized_event_id)s,
                          %(focus_end_normalized_event_id)s,
                          %(started_at)s,
                          %(ended_at)s,
                          %(duration_seconds)s,
                          %(end_reason)s,
                          %(is_open)s
                        )
                        on conflict (focus_start_normalized_event_id) do update
                        set focus_end_normalized_event_id = excluded.focus_end_normalized_event_id,
                            ended_at = excluded.ended_at,
                            duration_seconds = excluded.duration_seconds,
                            end_reason = excluded.end_reason,
                            is_open = excluded.is_open,
                            updated_at = timezone('utc', now())
                        """,
                        fact.__dict__,
                    )
        return len(facts)

    def complete_run(self, run_id: UUID, session_slice_count: int, idle_window_count: int, application_usage_count: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    update public.operational_fact_runs
                    set run_status = 'completed',
                        completed_at = timezone('utc', now()),
                        session_slice_count = %(session_slice_count)s,
                        idle_window_count = %(idle_window_count)s,
                        application_usage_count = %(application_usage_count)s
                    where id = %(run_id)s
                    """,
                    {
                        "run_id": run_id,
                        "session_slice_count": session_slice_count,
                        "idle_window_count": idle_window_count,
                        "application_usage_count": application_usage_count,
                    },
                )

    def fail_run(self, run_id: UUID, error_message: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    update public.operational_fact_runs
                    set run_status = 'failed',
                        completed_at = timezone('utc', now()),
                        error_message = %(error_message)s
                    where id = %(run_id)s
                    """,
                    {"run_id": run_id, "error_message": error_message[:2048]},
                )

