from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status

from app.repository import AuthorizationError, PostgresQueryRepository
from app.schemas import (
    ApplicationUsageItem,
    DailyMetricItem,
    IdleWindowItem,
    PaginatedResponse,
    SessionSliceItem,
)


@dataclass(frozen=True)
class ReadFilters:
    tenant_id: UUID
    date_from: date | None
    date_to: date | None
    workstation_id: UUID | None
    username: str | None
    limit: int
    offset: int


class QueryService:
    def __init__(self, repository: PostgresQueryRepository) -> None:
        self._repository = repository

    def _authorize(self, *, user_id: UUID, tenant_id: UUID):
        try:
            return self._repository.assert_member(user_id=user_id, tenant_id=tenant_id)
        except AuthorizationError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc

    def list_daily_metrics(self, *, user_id: UUID, filters: ReadFilters) -> PaginatedResponse[DailyMetricItem]:
        auth = self._authorize(user_id=user_id, tenant_id=filters.tenant_id)
        total, items = self._repository.get_daily_metrics(
            auth=auth,
            date_from=filters.date_from,
            date_to=filters.date_to,
            workstation_id=filters.workstation_id,
            username=filters.username,
            limit=filters.limit,
            offset=filters.offset,
        )
        return PaginatedResponse[DailyMetricItem](
            total=total,
            limit=filters.limit,
            offset=filters.offset,
            items=[DailyMetricItem.model_validate(item) for item in items],
        )

    def list_session_slices(self, *, user_id: UUID, filters: ReadFilters) -> PaginatedResponse[SessionSliceItem]:
        auth = self._authorize(user_id=user_id, tenant_id=filters.tenant_id)
        total, items = self._repository.get_session_slices(
            auth=auth,
            date_from=filters.date_from,
            date_to=filters.date_to,
            workstation_id=filters.workstation_id,
            username=filters.username,
            limit=filters.limit,
            offset=filters.offset,
        )
        return PaginatedResponse[SessionSliceItem](
            total=total,
            limit=filters.limit,
            offset=filters.offset,
            items=[SessionSliceItem.model_validate(item) for item in items],
        )

    def list_idle_windows(self, *, user_id: UUID, filters: ReadFilters) -> PaginatedResponse[IdleWindowItem]:
        auth = self._authorize(user_id=user_id, tenant_id=filters.tenant_id)
        total, items = self._repository.get_idle_windows(
            auth=auth,
            date_from=filters.date_from,
            date_to=filters.date_to,
            workstation_id=filters.workstation_id,
            username=filters.username,
            limit=filters.limit,
            offset=filters.offset,
        )
        return PaginatedResponse[IdleWindowItem](
            total=total,
            limit=filters.limit,
            offset=filters.offset,
            items=[IdleWindowItem.model_validate(item) for item in items],
        )

    def list_application_usage_facts(self, *, user_id: UUID, filters: ReadFilters) -> PaginatedResponse[ApplicationUsageItem]:
        auth = self._authorize(user_id=user_id, tenant_id=filters.tenant_id)
        total, items = self._repository.get_application_usage_facts(
            auth=auth,
            date_from=filters.date_from,
            date_to=filters.date_to,
            workstation_id=filters.workstation_id,
            username=filters.username,
            limit=filters.limit,
            offset=filters.offset,
        )
        return PaginatedResponse[ApplicationUsageItem](
            total=total,
            limit=filters.limit,
            offset=filters.offset,
            items=[ApplicationUsageItem.model_validate(item) for item in items],
        )

