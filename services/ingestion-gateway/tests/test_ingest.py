from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.repository import (
    AuthenticatedIngestionKey,
    IngestionRepository,
    PersistedEventResult,
    SourceScopeError,
)
from app.schemas import TelemetryBatchRequest
from app.service import TelemetryIngestionService


class FakeRepository(IngestionRepository):
    def __init__(self) -> None:
        self.auth_key = AuthenticatedIngestionKey(
            ingestion_api_key_id=UUID("00000000-0000-0000-0000-000000001501"),
            tenant_id=UUID("00000000-0000-0000-0000-000000000301"),
            key_prefix="local_ingest",
        )
        self.seen: dict[tuple[UUID, UUID], UUID] = {}

    def authenticate_ingestion_key(self, key_id: UUID, raw_key: str) -> AuthenticatedIngestionKey | None:
        if key_id == self.auth_key.ingestion_api_key_id and raw_key == "local-ingestion-key-change-me":
            return self.auth_key
        return None

    def validate_event_sources(self, tenant_id: UUID, events) -> None:
        for event in events:
            if str(event.source.workstation_id) != "00000000-0000-0000-0000-000000000901":
                raise SourceScopeError("one or more workstation ids are not in the authenticated tenant scope")

    def persist_raw_events(self, auth_key, request_id, batch, remote_address, user_agent):
        results: list[PersistedEventResult] = []
        for event in batch.events:
            key = (auth_key.tenant_id, event.event_id)
            if key in self.seen:
                results.append(
                    PersistedEventResult(
                        raw_event_id=self.seen[key],
                        source_event_id=event.event_id,
                        ingestion_status="duplicate",
                    )
                )
            else:
                raw_id = uuid4()
                self.seen[key] = raw_id
                results.append(
                    PersistedEventResult(
                        raw_event_id=raw_id,
                        source_event_id=event.event_id,
                        ingestion_status="accepted",
                    )
                )
        return results


def make_request() -> Request:
    return Request(
        {
            "type": "http",
            "headers": [(b"user-agent", b"pytest")],
            "client": ("127.0.0.1", 12345),
        }
    )


def make_batch(event_id: str, workstation_id: str = "00000000-0000-0000-0000-000000000901") -> TelemetryBatchRequest:
    return TelemetryBatchRequest.model_validate(
        {
            "schemaVersion": "2026-04-telemetry.v1",
            "batchId": "batch-001",
            "sentAt": "2026-04-12T12:00:00Z",
            "events": [
                {
                    "eventId": event_id,
                    "eventType": "heartbeat",
                    "occurredAt": "2026-04-12T11:59:58Z",
                    "source": {
                        "workstationId": workstation_id,
                        "agentInstallationId": "00000000-0000-0000-0000-000000001001",
                        "agentVersion": "0.1.0",
                    },
                    "payload": {
                        "status": "online",
                        "queueDepth": 0,
                    },
                }
            ],
        }
    )


def test_ingests_valid_batch() -> None:
    repository = FakeRepository()
    service = TelemetryIngestionService(repository=repository)

    auth_key = service.authenticate(
        key_id=UUID("00000000-0000-0000-0000-000000001501"),
        raw_key="local-ingestion-key-change-me",
    )
    response = service.ingest(
        auth_key=auth_key,
        batch=make_batch("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        request=make_request(),
    )

    assert response.accepted_count == 1
    assert response.duplicate_count == 0


def test_returns_duplicate_for_replayed_event() -> None:
    repository = FakeRepository()
    service = TelemetryIngestionService(repository=repository)
    auth_key = service.authenticate(
        key_id=UUID("00000000-0000-0000-0000-000000001501"),
        raw_key="local-ingestion-key-change-me",
    )
    batch = make_batch("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    first_response = service.ingest(auth_key=auth_key, batch=batch, request=make_request())
    second_response = service.ingest(auth_key=auth_key, batch=batch, request=make_request())

    assert first_response.accepted_count == 1
    assert second_response.accepted_count == 0
    assert second_response.duplicate_count == 1


def test_rejects_out_of_scope_workstation() -> None:
    repository = FakeRepository()
    service = TelemetryIngestionService(repository=repository)
    auth_key = service.authenticate(
        key_id=UUID("00000000-0000-0000-0000-000000001501"),
        raw_key="local-ingestion-key-change-me",
    )

    with pytest.raises(HTTPException) as exc_info:
        service.ingest(
            auth_key=auth_key,
            batch=make_batch(
                "cccccccc-cccc-cccc-cccc-cccccccccccc",
                workstation_id="99999999-9999-9999-9999-999999999999",
            ),
            request=make_request(),
        )

    assert exc_info.value.status_code == 403
    assert "tenant scope" in str(exc_info.value.detail)
