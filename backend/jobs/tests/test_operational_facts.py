from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.fact_repository import OperationalFactBatchResult, OperationalFactRepository
from app.fact_rules import (
    NormalizedEventRecord,
    derive_application_usage_facts,
    derive_idle_windows,
    derive_session_slices,
)
from app.fact_service import OperationalFactDerivationService, OperationalFactRequest

TENANT_ID = UUID("00000000-0000-0000-0000-000000000301")


def make_event(
    normalized_event_id: str,
    event_type: str,
    occurred_at: str,
    *,
    session_id: str | None = "session-001",
    username: str | None = "owner@local.test",
    app_name: str | None = None,
    process_name: str | None = None,
    idle_threshold_seconds: int | None = None,
) -> NormalizedEventRecord:
    return NormalizedEventRecord(
        normalized_event_id=UUID(normalized_event_id),
        tenant_id=TENANT_ID,
        workstation_id=UUID("00000000-0000-0000-0000-000000000901"),
        agent_installation_id=UUID("00000000-0000-0000-0000-000000001001"),
        normalized_event_type=event_type,
        occurred_at=datetime.fromisoformat(occurred_at.replace("Z", "+00:00")).astimezone(timezone.utc),
        session_id=session_id,
        username=username,
        app_name=app_name,
        process_name=process_name,
        idle_threshold_seconds=idle_threshold_seconds,
    )


class FakeOperationalFactRepository(OperationalFactRepository):
    def __init__(self, events: list[NormalizedEventRecord]) -> None:
        self.events = events
        self.session_slices = {}
        self.idle_windows = {}
        self.application_usage_facts = {}

    def start_run(self, tenant_id):
        return UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    def fetch_normalized_events(self, tenant_id):
        return self.events

    def persist_session_slices(self, facts):
        for fact in facts:
            self.session_slices[fact.start_normalized_event_id] = fact
        return len(self.session_slices)

    def persist_idle_windows(self, facts):
        for fact in facts:
            self.idle_windows[fact.start_normalized_event_id] = fact
        return len(self.idle_windows)

    def persist_application_usage_facts(self, facts):
        for fact in facts:
            self.application_usage_facts[fact.focus_start_normalized_event_id] = fact
        return len(self.application_usage_facts)

    def complete_run(self, run_id, session_slice_count, idle_window_count, application_usage_count):
        return None

    def fail_run(self, run_id, error_message):
        raise AssertionError(error_message)


def test_derives_closed_session_slice_from_login_to_logout() -> None:
    events = [
        make_event("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "session_login", "2026-04-12T12:00:00Z"),
        make_event("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "session_logout", "2026-04-12T12:30:00Z"),
    ]

    facts = derive_session_slices(events)

    assert len(facts) == 1
    assert facts[0].closure_reason == "explicit_session_end"
    assert facts[0].duration_seconds == 1800
    assert facts[0].is_open is False


def test_derives_idle_window_from_idle_start_to_idle_end() -> None:
    events = [
        make_event("cccccccc-cccc-cccc-cccc-cccccccccccc", "idle_start", "2026-04-12T12:10:00Z", idle_threshold_seconds=300),
        make_event("dddddddd-dddd-dddd-dddd-dddddddddddd", "idle_end", "2026-04-12T12:15:00Z"),
    ]

    facts = derive_idle_windows(events)

    assert len(facts) == 1
    assert facts[0].duration_seconds == 300
    assert facts[0].closure_reason == "explicit_idle_end"


def test_derives_application_usage_on_app_switch() -> None:
    events = [
        make_event(
            "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "foreground_application_change",
            "2026-04-12T12:01:00Z",
            app_name="Excel",
            process_name="EXCEL.EXE",
        ),
        make_event(
            "ffffffff-ffff-ffff-ffff-ffffffffffff",
            "foreground_application_change",
            "2026-04-12T12:06:00Z",
            app_name="Outlook",
            process_name="OUTLOOK.EXE",
        ),
    ]

    facts = derive_application_usage_facts(events)

    assert len(facts) == 2
    assert facts[0].app_name == "Excel"
    assert facts[0].duration_seconds == 300
    assert facts[0].end_reason == "app_switch"
    assert facts[1].is_open is True


def test_operational_fact_service_is_replay_safe() -> None:
    events = [
        make_event("11111111-1111-1111-1111-111111111111", "session_login", "2026-04-12T12:00:00Z"),
        make_event("22222222-2222-2222-2222-222222222222", "foreground_application_change", "2026-04-12T12:01:00Z", app_name="Excel"),
        make_event("33333333-3333-3333-3333-333333333333", "idle_start", "2026-04-12T12:05:00Z", idle_threshold_seconds=300),
        make_event("44444444-4444-4444-4444-444444444444", "idle_end", "2026-04-12T12:10:00Z"),
        make_event("55555555-5555-5555-5555-555555555555", "session_logout", "2026-04-12T12:30:00Z"),
    ]
    repository = FakeOperationalFactRepository(events)
    service = OperationalFactDerivationService(repository)

    first_result = service.run(OperationalFactRequest(tenant_id=TENANT_ID))
    second_result = service.run(OperationalFactRequest(tenant_id=TENANT_ID))

    assert first_result.session_slice_count == 1
    assert first_result.idle_window_count == 1
    assert first_result.application_usage_count == 1
    assert second_result.session_slice_count == 1
    assert second_result.idle_window_count == 1
    assert second_result.application_usage_count == 1
