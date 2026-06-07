from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.daily_metrics_repository import DailyMetricBatchResult, DailyMetricRepository
from app.daily_metrics_rules import derive_daily_user_operational_metrics


@dataclass(frozen=True)
class DailyMetricRequest:
    tenant_id: UUID
    metric_date: date | None = None


class DailyMetricDerivationService:
    def __init__(self, repository: DailyMetricRepository) -> None:
        self._repository = repository

    def run(self, request: DailyMetricRequest) -> DailyMetricBatchResult:
        run_id = self._repository.start_run(request.tenant_id, request.metric_date)

        try:
            session_slices = self._repository.fetch_session_slices(request.tenant_id, request.metric_date)
            idle_windows = self._repository.fetch_idle_windows(request.tenant_id, request.metric_date)
            application_usage_facts = self._repository.fetch_application_usage_facts(request.tenant_id, request.metric_date)
            metrics = derive_daily_user_operational_metrics(session_slices, idle_windows, application_usage_facts)
            metric_row_count = self._repository.persist_daily_metrics(metrics)
            self._repository.complete_run(run_id=run_id, metric_row_count=metric_row_count)
            return DailyMetricBatchResult(run_id=run_id, metric_row_count=metric_row_count)
        except Exception as exc:
            self._repository.fail_run(run_id=run_id, error_message=str(exc))
            raise
