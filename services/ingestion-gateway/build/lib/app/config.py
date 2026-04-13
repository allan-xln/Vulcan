from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    host: str
    port: int
    telemetry_schema_version: str


def get_settings() -> Settings:
    return Settings(
        database_url=getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/telemetry_app"),
        host=getenv("INGESTION_API_HOST", "0.0.0.0"),
        port=int(getenv("INGESTION_API_PORT", "8010")),
        telemetry_schema_version=getenv("INGESTION_SCHEMA_VERSION", "2026-04-telemetry.v1"),
    )

