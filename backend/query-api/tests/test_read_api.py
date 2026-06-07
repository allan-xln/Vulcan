from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.repository import AuthContext, AuthorizationError
from app.service import QueryService, ReadFilters


class FakeQueryRepository:
    def __init__(self) -> None:
        self.last_daily_metric_filters = None
        self.last_idle_window_filters = None

    def assert_member(self, user_id: UUID, tenant_id: UUID) -> AuthContext:
        if tenant_id != UUID("00000000-0000-0000-0000-000000000301"):
            raise AuthorizationError("user is not an active member of the tenant")
        return AuthContext(user_id=user_id, tenant_id=tenant_id)

    def get_daily_metrics(self, **kwargs):
        self.last_daily_metric_filters = kwargs
        return (
            1,
            [
                {
                    "id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                    "tenant_id": UUID("00000000-0000-0000-0000-000000000301"),
                    "metric_date": date(2026, 4, 12),
                    "workstation_id": UUID("00000000-0000-0000-0000-000000000901"),
                    "username": "owner@local.test",
                    "session_slice_count": 1,
                    "idle_window_count": 1,
                    "application_usage_count": 1,
                    "session_time_seconds": 1800,
                    "idle_time_seconds": 300,
                    "focused_app_usage_seconds": 240,
                }
            ],
        )

    def get_session_slices(self, **kwargs):
        return (
            1,
            [
                {
                    "id": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                    "tenant_id": UUID("00000000-0000-0000-0000-000000000301"),
                    "workstation_id": UUID("00000000-0000-0000-0000-000000000901"),
                    "session_id": "local-session-001",
                    "username": "owner@local.test",
                    "started_at": datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc),
                    "ended_at": datetime(2026, 4, 12, 12, 30, tzinfo=timezone.utc),
                    "duration_seconds": 1800,
                    "start_event_type": "session_login",
                    "end_event_type": "session_logout",
                    "closure_reason": "explicit_session_end",
                    "is_open": False,
                }
            ],
        )

    def get_idle_windows(self, **kwargs):
        self.last_idle_window_filters = kwargs
        return (
            1,
            [
                {
                    "id": UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
                    "tenant_id": UUID("00000000-0000-0000-0000-000000000301"),
                    "workstation_id": UUID("00000000-0000-0000-0000-000000000901"),
                    "session_id": "local-session-001",
                    "started_at": datetime(2026, 4, 12, 12, 5, tzinfo=timezone.utc),
                    "ended_at": datetime(2026, 4, 12, 12, 10, tzinfo=timezone.utc),
                    "duration_seconds": 300,
                    "idle_threshold_seconds": 300,
                    "closure_reason": "explicit_idle_end",
                    "is_open": False,
                }
            ],
        )

    def get_application_usage_facts(self, **kwargs):
        return (
            1,
            [
                {
                    "id": UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
                    "tenant_id": UUID("00000000-0000-0000-0000-000000000301"),
                    "workstation_id": UUID("00000000-0000-0000-0000-000000000901"),
                    "session_id": "local-session-001",
                    "app_name": "Excel",
                    "process_name": "EXCEL.EXE",
                    "started_at": datetime(2026, 4, 12, 12, 1, tzinfo=timezone.utc),
                    "ended_at": datetime(2026, 4, 12, 12, 5, tzinfo=timezone.utc),
                    "duration_seconds": 240,
                    "end_reason": "idle_start",
                    "is_open": False,
                }
            ],
        )


def build_filters(**overrides) -> ReadFilters:
    base = {
        "tenant_id": UUID("00000000-0000-0000-0000-000000000301"),
        "date_from": date(2026, 4, 12),
        "date_to": date(2026, 4, 12),
        "workstation_id": UUID("00000000-0000-0000-0000-000000000901"),
        "username": "owner@local.test",
        "limit": 50,
        "offset": 0,
    }
    base.update(overrides)
    return ReadFilters(**base)


def test_daily_metrics_response_maps_snake_case_repository_rows() -> None:
    repository = FakeQueryRepository()
    service = QueryService(repository=repository)

    response = service.list_daily_metrics(
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        filters=build_filters(),
    )

    assert response.total == 1
    assert response.items[0].tenant_id == UUID("00000000-0000-0000-0000-000000000301")
    assert response.items[0].session_time_seconds == 1800


def test_idle_windows_pass_username_filter_through_to_repository() -> None:
    repository = FakeQueryRepository()
    service = QueryService(repository=repository)

    response = service.list_idle_windows(
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        filters=build_filters(username="owner@local.test"),
    )

    assert response.items[0].duration_seconds == 300
    assert repository.last_idle_window_filters["username"] == "owner@local.test"


def test_session_slices_response_preserves_closure_fields() -> None:
    repository = FakeQueryRepository()
    service = QueryService(repository=repository)

    response = service.list_session_slices(
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        filters=build_filters(),
    )

    assert response.items[0].closure_reason == "explicit_session_end"
    assert response.items[0].end_event_type == "session_logout"


def test_query_service_blocks_user_without_membership() -> None:
    repository = FakeQueryRepository()
    service = QueryService(repository=repository)

    with pytest.raises(HTTPException) as exc_info:
        service.list_application_usage_facts(
            user_id=UUID("11111111-1111-1111-1111-111111111111"),
            filters=build_filters(tenant_id=UUID("99999999-9999-9999-9999-999999999999")),
        )

    assert exc_info.value.status_code == 403
