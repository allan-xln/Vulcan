from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException, Request, status

from app.repository import (
    AuthenticatedIngestionKey,
    IngestionRepository,
    PersistedEventResult,
    SourceScopeError,
)
from app.schemas import AcceptedEvent, TelemetryBatchRequest, TelemetryBatchResponse


class TelemetryIngestionService:
    def __init__(self, repository: IngestionRepository) -> None:
        self._repository = repository

    def authenticate(self, key_id: UUID, raw_key: str) -> AuthenticatedIngestionKey:
        auth_key = self._repository.authenticate_ingestion_key(key_id=key_id, raw_key=raw_key)
        if auth_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid ingestion credentials",
            )
        return auth_key

    def ingest(
        self,
        auth_key: AuthenticatedIngestionKey,
        batch: TelemetryBatchRequest,
        request: Request,
    ) -> TelemetryBatchResponse:
        try:
            self._repository.validate_event_sources(auth_key.tenant_id, batch.events)
        except SourceScopeError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc

        request_id = uuid4()
        persisted = self._repository.persist_raw_events(
            auth_key=auth_key,
            request_id=request_id,
            batch=batch,
            remote_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        accepted = sum(1 for item in persisted if item.ingestion_status == "accepted")
        duplicates = sum(1 for item in persisted if item.ingestion_status == "duplicate")

        return TelemetryBatchResponse(
            requestId=request_id,
            tenantId=auth_key.tenant_id,
            acceptedCount=accepted,
            duplicateCount=duplicates,
            results=[self._to_accepted_event(item) for item in persisted],
        )

    @staticmethod
    def _to_accepted_event(item: PersistedEventResult) -> AcceptedEvent:
        return AcceptedEvent(
            sourceEventId=item.source_event_id,
            ingestionStatus=item.ingestion_status,
            rawEventId=item.raw_event_id,
        )

