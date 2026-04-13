from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Query

from app.repository import PostgresQueryRepository
from app.schemas import (
    ApplicationUsageItem,
    DailyMetricItem,
    HealthResponse,
    IdleWindowItem,
    PaginatedResponse,
    SessionSliceItem,
)
from app.service import QueryService, ReadFilters


app = FastAPI(title="Query API", version="0.1.0")


def get_repository() -> PostgresQueryRepository:
    return PostgresQueryRepository()


def get_service(repository: PostgresQueryRepository = Depends(get_repository)) -> QueryService:
    return QueryService(repository=repository)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="query-api",
        data_boundary="postgres-read-api",
    )


def build_filters(
    tenant_id: UUID = Query(alias="tenantId"),
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    workstation_id: UUID | None = Query(default=None, alias="workstationId"),
    username: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ReadFilters:
    return ReadFilters(
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        workstation_id=workstation_id,
        username=username,
        limit=limit,
        offset=offset,
    )


@app.get("/v1/daily-user-operational-metrics", response_model=PaginatedResponse[DailyMetricItem])
def list_daily_metrics(
    filters: ReadFilters = Depends(build_filters),
    service: QueryService = Depends(get_service),
    user_id: UUID = Header(alias="X-User-Id"),
) -> PaginatedResponse[DailyMetricItem]:
    return service.list_daily_metrics(user_id=user_id, filters=filters)


@app.get("/v1/session-slices", response_model=PaginatedResponse[SessionSliceItem])
def list_session_slices(
    filters: ReadFilters = Depends(build_filters),
    service: QueryService = Depends(get_service),
    user_id: UUID = Header(alias="X-User-Id"),
) -> PaginatedResponse[SessionSliceItem]:
    return service.list_session_slices(user_id=user_id, filters=filters)


@app.get("/v1/idle-windows", response_model=PaginatedResponse[IdleWindowItem])
def list_idle_windows(
    filters: ReadFilters = Depends(build_filters),
    service: QueryService = Depends(get_service),
    user_id: UUID = Header(alias="X-User-Id"),
) -> PaginatedResponse[IdleWindowItem]:
    return service.list_idle_windows(user_id=user_id, filters=filters)


@app.get("/v1/application-usage-facts", response_model=PaginatedResponse[ApplicationUsageItem])
def list_application_usage_facts(
    filters: ReadFilters = Depends(build_filters),
    service: QueryService = Depends(get_service),
    user_id: UUID = Header(alias="X-User-Id"),
) -> PaginatedResponse[ApplicationUsageItem]:
    return service.list_application_usage_facts(user_id=user_id, filters=filters)
