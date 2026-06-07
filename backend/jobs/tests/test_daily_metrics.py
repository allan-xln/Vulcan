from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from app.daily_metrics_repository import DailyMetricBatchResult, DailyMetricRepository
from app.daily_metrics_rules import (
    ApplicationUsageRecord,
    IdleWindowRecord,
    SessionSliceRecord,
    derive_daily_user_operational_metrics,
)
from app.daily_metrics_service import DailyMetricDerivationService, DailyMetricRequest

TENANT_ID = UUID("00000000-0000-0000-0000-000000000301")


class FakeDailyMetricRepository(DailyMetricRepository):
    def __init__(
        self,
        session_slices: list[SessionSliceRecord],
        idle_windows: list[IdleWindowRecord],
        application_usage_facts: list[ApplicationUsageRecord],
    ) -> None:
        self.session_slices = session_slices
        self.idle_windows = idle_windows
        self.application_usage_facts = application_usage_facts
        self.persisted = {}

    def start_run(self, tenant_id, metric_date):
        return UUID("aaaaaaaa-bbbb-cccc-dddd-ffffffffffff")

    def fetch_session_slices(self, tenant_id, metric_date):
        return self.session_slices

    def fetch_idle_windows(self, tenant_id, metric_date):
        return self.idle_windows

    def fetch_application_usage_facts(self, tenant_id, metric_date):
        return self.application_usage_facts

    def persist_daily_metrics(self, metrics):
        for metric in metrics:
            self.persisted[(metric.tenant_id, metric.metric_date, metric.workstation_id, metric.username)] = metric
        return len(self.persisted)

    def complete_run(self, run_id, metric_row_count):
        return None

    def fail_run(self, run_id, error_message):
        raise AssertionError(error_message)


def test_derive_daily_metrics_sums_closed_facts() -> None:
    tenant_id = TENANT_ID
    workstation_id = UUID("00000000-0000-0000-0000-000000000901")
    metric_date = date(2026, 4, 12)

    metrics = derive_daily_user_operational_metrics(
        session_slices=[
            SessionSliceRecord(
                tenant_id=tenant_id,
                workstation_id=workstation_id,
                username="owner@local.test",
                started_at=datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc),
                duration_seconds=1800,
                is_open=False,
            )
        ],
        idle_windows=[
            IdleWindowRecord(
                tenant_id=tenant_id,
                workstation_id=workstation_id,
                username="owner@local.test",
                started_at=datetime(2026, 4, 12, 12, 5, tzinfo=timezone.utc),
                duration_seconds=300,
                is_open=False,
            )
        ],
        application_usage_facts=[
            ApplicationUsageRecord(
                tenant_id=tenant_id,
                workstation_id=workstation_id,
                username="owner@local.test",
                started_at=datetime(2026, 4, 12, 12, 1, tzinfo=timezone.utc),
                duration_seconds=240,
                is_open=False,
            )
        ],
    )

    assert len(metrics) == 1
    user_metric = metrics[0]

    assert user_metric.metric_date == metric_date
    assert user_metric.session_time_seconds == 1800
    assert user_metric.focused_app_usage_seconds == 240
    assert user_metric.idle_time_seconds == 300
    assert user_metric.session_slice_count == 1
    assert user_metric.idle_window_count == 1
    assert user_metric.application_usage_count == 1


def test_derive_daily_metrics_ignores_open_facts() -> None:
    tenant_id = TENANT_ID
    workstation_id = UUID("00000000-0000-0000-0000-000000000901")

    metrics = derive_daily_user_operational_metrics(
        session_slices=[
            SessionSliceRecord(
                tenant_id=tenant_id,
                workstation_id=workstation_id,
                username="owner@local.test",
                started_at=datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc),
                duration_seconds=None,
                is_open=True,
            )
        ],
        idle_windows=[],
        application_usage_facts=[],
    )

    assert metrics == []


def test_daily_metric_service_is_replay_safe() -> None:
    tenant_id = TENANT_ID
    workstation_id = UUID("00000000-0000-0000-0000-000000000901")
    repository = FakeDailyMetricRepository(
        session_slices=[
            SessionSliceRecord(
                tenant_id=tenant_id,
                workstation_id=workstation_id,
                username="owner@local.test",
                started_at=datetime(2026, 4, 12, 12, 0, tzinfo=timezone.utc),
                duration_seconds=1800,
                is_open=False,
            )
        ],
        idle_windows=[],
        application_usage_facts=[],
    )
    service = DailyMetricDerivationService(repository=repository)

    first_result = service.run(DailyMetricRequest(tenant_id=tenant_id))
    second_result = service.run(DailyMetricRequest(tenant_id=tenant_id))

    assert first_result.metric_row_count == 1
    assert second_result.metric_row_count == 1
