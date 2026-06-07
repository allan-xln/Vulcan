from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    host: str
    port: int


def get_settings() -> Settings:
    return Settings(
        database_url=getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/vulcan"),
        host=getenv("QUERY_API_HOST", "0.0.0.0"),
        port=int(getenv("QUERY_API_PORT", "8020")),
    )

