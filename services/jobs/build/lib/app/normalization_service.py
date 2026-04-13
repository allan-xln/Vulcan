from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.normalization_repository import NormalizationBatchResult, NormalizationRepository
from app.normalization_rules import normalize_raw_event


@dataclass(frozen=True)
class NormalizationRequest:
    tenant_id: UUID | None = None
    batch_limit: int = 500


class TelemetryNormalizationService:
    def __init__(self, repository: NormalizationRepository) -> None:
        self._repository = repository

    def run(self, request: NormalizationRequest) -> NormalizationBatchResult:
        run_id = self._repository.start_run(request.tenant_id)

        try:
            raw_events = self._repository.fetch_pending_raw_events(
                tenant_id=request.tenant_id,
                limit=request.batch_limit,
            )
            normalized_events = [normalize_raw_event(event) for event in raw_events]
            processed_count, duplicate_count = self._repository.persist_normalized_events(normalized_events)
            self._repository.complete_run(
                run_id=run_id,
                processed_count=processed_count,
                duplicate_count=duplicate_count,
            )
            return NormalizationBatchResult(
                normalization_run_id=run_id,
                processed_count=processed_count,
                duplicate_count=duplicate_count,
            )
        except Exception as exc:
            self._repository.fail_run(run_id=run_id, error_message=str(exc))
            raise

