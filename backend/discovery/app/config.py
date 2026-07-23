from __future__ import annotations

from dataclasses import dataclass
from os import getenv


def _bool_env(name: str, default: bool = False) -> bool:
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_list_env(name: str, default: tuple[int, ...]) -> tuple[int, ...]:
    value = getenv(name)
    if not value:
        return default
    ports = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    if any(port < 1 or port > 65535 for port in ports):
        raise ValueError(f"{name} contains an invalid TCP port")
    return ports


@dataclass(frozen=True)
class DiscoverySettings:
    database_url: str
    enabled: bool
    worker_poll_seconds: int
    max_targets_per_run: int
    max_concurrency: int
    allow_public_networks: bool
    max_timeout_ms: int
    allowed_tcp_ports: tuple[int, ...]
    health_file: str


def get_settings() -> DiscoverySettings:
    return DiscoverySettings(
        database_url=getenv("DATABASE_URL", ""),
        enabled=_bool_env("DISCOVERY_ENABLED", False),
        worker_poll_seconds=max(2, int(getenv("DISCOVERY_WORKER_POLL_SECONDS", "10"))),
        max_targets_per_run=max(1, min(int(getenv("DISCOVERY_MAX_TARGETS_PER_RUN", "256")), 4096)),
        max_concurrency=max(1, min(int(getenv("DISCOVERY_MAX_CONCURRENCY", "16")), 32)),
        allow_public_networks=_bool_env("DISCOVERY_ALLOW_PUBLIC_NETWORKS", False),
        max_timeout_ms=max(100, min(int(getenv("DISCOVERY_MAX_TIMEOUT_MS", "2000")), 10000)),
        allowed_tcp_ports=_int_list_env(
            "DISCOVERY_ALLOWED_TCP_PORTS",
            (22, 53, 80, 443, 445, 515, 631, 9100),
        ),
        health_file=getenv("DISCOVERY_HEALTH_FILE", "/tmp/vulcan-discovery-health.json"),
    )
