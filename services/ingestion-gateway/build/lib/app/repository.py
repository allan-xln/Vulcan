from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from app.config import get_settings
from app.schemas import TelemetryBatchRequest, TelemetryEvent

if TYPE_CHECKING:
    from psycopg import Connection


@dataclass(frozen=True)
class AuthenticatedIngestionKey:
    ingestion_api_key_id: UUID
    tenant_id: UUID
    key_prefix: str


@dataclass(frozen=True)
class PersistedEventResult:
    raw_event_id: UUID
    source_event_id: UUID
    ingestion_status: str


class IngestionRepository(Protocol):
    def authenticate_ingestion_key(self, key_id: UUID, raw_key: str) -> AuthenticatedIngestionKey | None: ...
    def validate_event_sources(self, tenant_id: UUID, events: list[TelemetryEvent]) -> None: ...
    def persist_raw_events(
        self,
        auth_key: AuthenticatedIngestionKey,
        request_id: UUID,
        batch: TelemetryBatchRequest,
        remote_address: str | None,
        user_agent: str | None,
    ) -> list[PersistedEventResult]: ...


class SourceScopeError(ValueError):
    pass


class PostgresIngestionRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or get_settings().database_url

    def _connect(self) -> "Connection":
        from psycopg import connect
        from psycopg.rows import dict_row

        return connect(self._database_url, row_factory=dict_row)

    def authenticate_ingestion_key(self, key_id: UUID, raw_key: str) -> AuthenticatedIngestionKey | None:
        hashed_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    select id, tenant_id, key_prefix
                    from public.ingestion_api_keys
                    where id = %(key_id)s
                      and key_hash = %(key_hash)s
                      and status = 'active'
                      and (expires_at is null or expires_at > timezone('utc', now()))
                      and scopes @> array['telemetry:ingest']::text[]
                    """,
                    {"key_id": key_id, "key_hash": hashed_key},
                )
                row = cursor.fetchone()

                if row is None:
                    return None

                cursor.execute(
                    """
                    update public.ingestion_api_keys
                    set last_used_at = timezone('utc', now()),
                        updated_at = timezone('utc', now())
                    where id = %(key_id)s
                    """,
                    {"key_id": key_id},
                )

        return AuthenticatedIngestionKey(
            ingestion_api_key_id=row["id"],
            tenant_id=row["tenant_id"],
            key_prefix=row["key_prefix"],
        )

    def validate_event_sources(self, tenant_id: UUID, events: list[TelemetryEvent]) -> None:
        workstation_ids = sorted({event.source.workstation_id for event in events})
        agent_installation_ids = sorted(
            {event.source.agent_installation_id for event in events if event.source.agent_installation_id is not None}
        )

        with self._connect() as conn:
            with conn.cursor() as cursor:
                if workstation_ids:
                    cursor.execute(
                        """
                        select id
                        from public.workstations
                        where tenant_id = %(tenant_id)s
                          and id = any(%(workstation_ids)s::uuid[])
                        """,
                        {"tenant_id": tenant_id, "workstation_ids": workstation_ids},
                    )
                    found_workstation_ids = {row["id"] for row in cursor.fetchall()}
                    if found_workstation_ids != set(workstation_ids):
                        raise SourceScopeError("one or more workstation ids are not in the authenticated tenant scope")

                if agent_installation_ids:
                    cursor.execute(
                        """
                        select id, workstation_id
                        from public.agent_installations
                        where tenant_id = %(tenant_id)s
                          and id = any(%(agent_installation_ids)s::uuid[])
                          and status = 'active'
                        """,
                        {"tenant_id": tenant_id, "agent_installation_ids": agent_installation_ids},
                    )
                    found_installations = {row["id"]: row["workstation_id"] for row in cursor.fetchall()}

                    if set(found_installations.keys()) != set(agent_installation_ids):
                        raise SourceScopeError("one or more agent installation ids are not active in the authenticated tenant scope")

                    for event in events:
                        installation_id = event.source.agent_installation_id
                        if installation_id is None:
                            continue
                        if found_installations[installation_id] != event.source.workstation_id:
                            raise SourceScopeError("agent installation does not belong to the workstation declared in the event")

    def persist_raw_events(
        self,
        auth_key: AuthenticatedIngestionKey,
        request_id: UUID,
        batch: TelemetryBatchRequest,
        remote_address: str | None,
        user_agent: str | None,
    ) -> list[PersistedEventResult]:
        results: list[PersistedEventResult] = []

        with self._connect() as conn:
            with conn.cursor() as cursor:
                for event in batch.events:
                    payload_json = json.dumps(event.model_dump(mode="json", by_alias=True), sort_keys=True)
                    payload_sha = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

                    cursor.execute(
                        """
                        insert into public.raw_telemetry_intake (
                          tenant_id,
                          ingestion_api_key_id,
                          agent_installation_id,
                          workstation_id,
                          request_id,
                          batch_id,
                          source_event_id,
                          schema_version,
                          event_type,
                          occurred_at,
                          payload_sha256,
                          ingestion_status,
                          event_payload,
                          request_metadata
                        )
                        values (
                          %(tenant_id)s,
                          %(ingestion_api_key_id)s,
                          %(agent_installation_id)s,
                          %(workstation_id)s,
                          %(request_id)s,
                          %(batch_id)s,
                          %(source_event_id)s,
                          %(schema_version)s,
                          %(event_type)s,
                          %(occurred_at)s,
                          %(payload_sha256)s,
                          'accepted',
                          %(event_payload)s::jsonb,
                          %(request_metadata)s::jsonb
                        )
                        on conflict (tenant_id, source_event_id) do nothing
                        returning id
                        """,
                        {
                            "tenant_id": auth_key.tenant_id,
                            "ingestion_api_key_id": auth_key.ingestion_api_key_id,
                            "agent_installation_id": event.source.agent_installation_id,
                            "workstation_id": event.source.workstation_id,
                            "request_id": request_id,
                            "batch_id": batch.batch_id,
                            "source_event_id": event.event_id,
                            "schema_version": batch.schema_version,
                            "event_type": event.event_type,
                            "occurred_at": event.occurred_at.astimezone(timezone.utc),
                            "payload_sha256": payload_sha,
                            "event_payload": payload_json,
                            "request_metadata": json.dumps(
                                {
                                    "remoteAddress": remote_address,
                                    "userAgent": user_agent,
                                    "sentAt": batch.sent_at.astimezone(timezone.utc).isoformat(),
                                    "receivedAt": datetime.now(timezone.utc).isoformat(),
                                },
                                sort_keys=True,
                            ),
                        },
                    )
                    inserted = cursor.fetchone()

                    if inserted is not None:
                        results.append(
                            PersistedEventResult(
                                raw_event_id=inserted["id"],
                                source_event_id=event.event_id,
                                ingestion_status="accepted",
                            )
                        )
                        continue

                    cursor.execute(
                        """
                        select id
                        from public.raw_telemetry_intake
                        where tenant_id = %(tenant_id)s
                          and source_event_id = %(source_event_id)s
                        """,
                        {
                            "tenant_id": auth_key.tenant_id,
                            "source_event_id": event.event_id,
                        },
                    )
                    duplicate_row = cursor.fetchone()
                    results.append(
                        PersistedEventResult(
                            raw_event_id=duplicate_row["id"],
                            source_event_id=event.event_id,
                            ingestion_status="duplicate",
                        )
                    )

        return results
