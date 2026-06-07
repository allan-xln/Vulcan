from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.normalization_repository import NormalizationBatchResult, NormalizationRepository
from app.normalization_rules import NormalizedOperationalEvent, RawOperationalEventRecord, normalize_raw_event
from app.normalization_service import NormalizationRequest, OperationalEventNormalizationService

TENANT_ID = UUID("00000000-0000-0000-0000-000000000301")


class FakeNormalizationRepository(NormalizationRepository):
    def __init__(self, raw_events: list[RawOperationalEventRecord]) -> None:
        self.raw_events = raw_events
        self.persisted: dict[UUID, NormalizedOperationalEvent] = {}
        self.failed_error_message: str | None = None

    def start_run(self, tenant_id):
        return UUID("11111111-2222-3333-4444-555555555555")

    def fetch_pending_raw_events(self, tenant_id, limit):
        return self.raw_events[:limit]

    def persist_normalized_events(self, events):
        processed_count = 0
        duplicate_count = 0
        for event in events:
            if event.raw_event_id in self.persisted:
                duplicate_count += 1
            else:
                self.persisted[event.raw_event_id] = event
                processed_count += 1
        return processed_count, duplicate_count

    def complete_run(self, run_id, processed_count, duplicate_count):
        return None

    def fail_run(self, run_id, error_message):
        self.failed_error_message = error_message


def make_raw_event(event_type: str, payload: dict, source_event_id: str) -> RawOperationalEventRecord:
    return RawOperationalEventRecord(
        raw_event_id=uuid4(),
        tenant_id=TENANT_ID,
        source_event_id=UUID(source_event_id),
        workstation_id=UUID("00000000-0000-0000-0000-000000000901"),
        agent_installation_id=UUID("00000000-0000-0000-0000-000000001001"),
        schema_version="2026-06-operational-events.v1",
        event_type=event_type,
        occurred_at=datetime(2026, 4, 12, 12, 0, 0, tzinfo=timezone.utc),
        received_at=datetime(2026, 4, 12, 12, 0, 1, tzinfo=timezone.utc),
        event_payload={
            "eventType": event_type,
            "source": {
                "workstationId": "00000000-0000-0000-0000-000000000901",
                "agentInstallationId": "00000000-0000-0000-0000-000000001001",
            },
            "payload": payload,
        },
    )


def test_normalize_foreground_application_change_extracts_explicit_fields() -> None:
    raw_event = make_raw_event(
        "foreground_application_change",
        {
            "sessionId": "session-001",
            "appName": "Excel",
            "executablePath": "C:/Program Files/Microsoft Office/root/Office16/EXCEL.EXE",
            "windowTitle": "Budget FY26",
        },
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    )

    normalized_event = normalize_raw_event(raw_event)

    assert normalized_event.normalized_event_type == "foreground_application_change"
    assert normalized_event.session_id == "session-001"
    assert normalized_event.app_name == "Excel"
    assert normalized_event.process_name is None
    assert normalized_event.queue_depth is None


def test_normalization_service_is_replay_safe() -> None:
    raw_event = make_raw_event(
        "heartbeat",
        {"status": "online", "queueDepth": 2},
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    )
    repository = FakeNormalizationRepository(raw_events=[raw_event])
    service = OperationalEventNormalizationService(repository=repository)

    first_result = service.run(NormalizationRequest(tenant_id=TENANT_ID, batch_limit=10))
    second_result = service.run(NormalizationRequest(tenant_id=TENANT_ID, batch_limit=10))

    assert first_result.processed_count == 1
    assert first_result.duplicate_count == 0
    assert second_result.processed_count == 0
    assert second_result.duplicate_count == 1


def test_normalize_idle_event_extracts_idle_threshold_and_session_id() -> None:
    raw_event = make_raw_event(
        "idle_start",
        {"sessionId": "session-123", "idleThresholdSeconds": 300},
        "cccccccc-cccc-cccc-cccc-cccccccccccc",
    )

    normalized_event = normalize_raw_event(raw_event)

    assert normalized_event.session_id == "session-123"
    assert normalized_event.idle_threshold_seconds == 300
