from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.fact_repository import OperationalFactBatchResult, OperationalFactRepository
from app.fact_rules import derive_application_usage_facts, derive_idle_windows, derive_session_slices


@dataclass(frozen=True)
class OperationalFactRequest:
    tenant_id: UUID | None = None


class OperationalFactDerivationService:
    def __init__(self, repository: OperationalFactRepository) -> None:
        self._repository = repository

    def run(self, request: OperationalFactRequest) -> OperationalFactBatchResult:
        run_id = self._repository.start_run(request.tenant_id)

        try:
            normalized_events = self._repository.fetch_normalized_events(request.tenant_id)
            session_slices = derive_session_slices(normalized_events)
            idle_windows = derive_idle_windows(normalized_events)
            application_usage_facts = derive_application_usage_facts(normalized_events)

            session_slice_count = self._repository.persist_session_slices(session_slices)
            idle_window_count = self._repository.persist_idle_windows(idle_windows)
            application_usage_count = self._repository.persist_application_usage_facts(application_usage_facts)

            self._repository.complete_run(
                run_id=run_id,
                session_slice_count=session_slice_count,
                idle_window_count=idle_window_count,
                application_usage_count=application_usage_count,
            )
            return OperationalFactBatchResult(
                run_id=run_id,
                session_slice_count=session_slice_count,
                idle_window_count=idle_window_count,
                application_usage_count=application_usage_count,
            )
        except Exception as exc:
            self._repository.fail_run(run_id=run_id, error_message=str(exc))
            raise

