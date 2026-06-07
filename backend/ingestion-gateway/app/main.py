from uuid import UUID

from fastapi import Depends, FastAPI, Header, Request
from pydantic import BaseModel

from app.repository import IngestionRepository, PostgresIngestionRepository
from app.schemas import OperationalEventBatchRequest, OperationalEventBatchResponse
from app.service import OperationalEventIngestionService


class HealthResponse(BaseModel):
    status: str
    service: str
    intake_boundary: str


app = FastAPI(title="Ingestion Gateway", version="0.1.0")


def get_repository() -> IngestionRepository:
    return PostgresIngestionRepository()


def get_service(repository: IngestionRepository = Depends(get_repository)) -> OperationalEventIngestionService:
    return OperationalEventIngestionService(repository=repository)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="ingestion-gateway",
        intake_boundary="postgres-raw-intake",
    )


@app.post("/v1/operational-events/batches", response_model=OperationalEventBatchResponse)
def ingest_events(
    batch: OperationalEventBatchRequest,
    request: Request,
    service: OperationalEventIngestionService = Depends(get_service),
    ingestion_key_id: UUID = Header(alias="X-Ingestion-Key-Id"),
    ingestion_key: str = Header(alias="X-Ingestion-Key", min_length=16, max_length=256),
) -> OperationalEventBatchResponse:
    auth_key = service.authenticate(key_id=ingestion_key_id, raw_key=ingestion_key)
    return service.ingest(auth_key=auth_key, batch=batch, request=request)

