from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from app.normalization_rules import NormalizedOperationalEvent, RawTelemetryRecord

if TYPE_CHECKING:
    from psycopg import Connection


@dataclass(frozen=True)
class NormalizationBatchResult:
    normalization_run_id: UUID
    processed_count: int
    duplicate_count: int


class NormalizationRepository(Protocol):
    def start_run(self, tenant_id: UUID | None) -> UUID: ...
    def fetch_pending_raw_events(self, tenant_id: UUID | None, limit: int) -> list[RawTelemetryRecord]: ...
    def persist_normalized_events(self, events: list[NormalizedOperationalEvent]) -> tuple[int, int]: ...
    def complete_run(self, run_id: UUID, processed_count: int, duplicate_count: int) -> None: ...
    def fail_run(self, run_id: UUID, error_message: str) -> None: ...


class PostgresNormalizationRepository:
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
                    insert into public.normalization_runs (tenant_id, run_status)
                    values (%(tenant_id)s, 'running')
                    returning id
                    """,
                    {"tenant_id": tenant_id},
                )
                row = cursor.fetchone()
        return row["id"]

    def fetch_pending_raw_events(self, tenant_id: UUID | None, limit: int) -> list[RawTelemetryRecord]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    select
                      r.id as raw_event_id,
                      r.tenant_id,
                      r.source_event_id,
                      r.workstation_id,
                      r.agent_installation_id,
                      r.schema_version,
                      r.event_type,
                      r.occurred_at,
                      r.received_at,
                      r.event_payload
                    from public.raw_telemetry_intake r
                    left join public.normalized_operational_events n
                      on n.raw_telemetry_intake_id = r.id
                    where r.ingestion_status = 'accepted'
                      and n.id is null
                      and (%(tenant_id)s::uuid is null or r.tenant_id = %(tenant_id)s::uuid)
                    order by r.received_at, r.id
                    limit %(limit)s
                    """,
                    {"tenant_id": tenant_id, "limit": limit},
                )
                rows = cursor.fetchall()

        return [
            RawTelemetryRecord(
                raw_event_id=row["raw_event_id"],
                tenant_id=row["tenant_id"],
                source_event_id=row["source_event_id"],
                workstation_id=row["workstation_id"],
                agent_installation_id=row["agent_installation_id"],
                schema_version=row["schema_version"],
                event_type=row["event_type"],
                occurred_at=row["occurred_at"],
                received_at=row["received_at"],
                event_payload=row["event_payload"],
            )
            for row in rows
        ]

    def persist_normalized_events(self, events: list[NormalizedOperationalEvent]) -> tuple[int, int]:
        processed_count = 0
        duplicate_count = 0

        with self._connect() as conn:
            with conn.cursor() as cursor:
                for event in events:
                    cursor.execute(
                        """
                        insert into public.normalized_operational_events (
                          tenant_id,
                          raw_telemetry_intake_id,
                          source_event_id,
                          workstation_id,
                          agent_installation_id,
                          normalized_event_type,
                          schema_version,
                          occurred_at,
                          received_at,
                          session_id,
                          username,
                          app_name,
                          process_name,
                          queue_depth,
                          idle_threshold_seconds,
                          normalized_payload
                        )
                        values (
                          %(tenant_id)s,
                          %(raw_telemetry_intake_id)s,
                          %(source_event_id)s,
                          %(workstation_id)s,
                          %(agent_installation_id)s,
                          %(normalized_event_type)s,
                          %(schema_version)s,
                          %(occurred_at)s,
                          %(received_at)s,
                          %(session_id)s,
                          %(username)s,
                          %(app_name)s,
                          %(process_name)s,
                          %(queue_depth)s,
                          %(idle_threshold_seconds)s,
                          %(normalized_payload)s::jsonb
                        )
                        on conflict (raw_telemetry_intake_id) do nothing
                        """,
                        {
                            "tenant_id": event.tenant_id,
                            "raw_telemetry_intake_id": event.raw_event_id,
                            "source_event_id": event.source_event_id,
                            "workstation_id": event.workstation_id,
                            "agent_installation_id": event.agent_installation_id,
                            "normalized_event_type": event.normalized_event_type,
                            "schema_version": event.schema_version,
                            "occurred_at": event.occurred_at,
                            "received_at": event.received_at,
                            "session_id": event.session_id,
                            "username": event.username,
                            "app_name": event.app_name,
                            "process_name": event.process_name,
                            "queue_depth": event.queue_depth,
                            "idle_threshold_seconds": event.idle_threshold_seconds,
                            "normalized_payload": json.dumps(event.normalized_payload, sort_keys=True),
                        },
                    )
                    if cursor.rowcount == 1:
                        processed_count += 1
                    else:
                        duplicate_count += 1

        return processed_count, duplicate_count

    def complete_run(self, run_id: UUID, processed_count: int, duplicate_count: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    update public.normalization_runs
                    set run_status = 'completed',
                        completed_at = timezone('utc', now()),
                        processed_count = %(processed_count)s,
                        duplicate_count = %(duplicate_count)s
                    where id = %(run_id)s
                    """,
                    {
                        "run_id": run_id,
                        "processed_count": processed_count,
                        "duplicate_count": duplicate_count,
                    },
                )

    def fail_run(self, run_id: UUID, error_message: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    update public.normalization_runs
                    set run_status = 'failed',
                        completed_at = timezone('utc', now()),
                        error_message = %(error_message)s
                    where id = %(run_id)s
                    """,
                    {"run_id": run_id, "error_message": error_message[:2048]},
                )

