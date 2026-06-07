from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    host: str
    port: int
    operational_event_schema_version: str


def get_settings() -> Settings:
    return Settings(
        database_url=getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/vulcan"),
        host=getenv("INGESTION_API_HOST", "0.0.0.0"),
        port=int(getenv("INGESTION_API_PORT", "8010")),
        operational_event_schema_version=getenv("INGESTION_SCHEMA_VERSION", "2026-06-operational-events.v1"),
    )

