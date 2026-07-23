from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdapterContext:
    tenant_id: str
    integration_id: str
    site_id: str | None = None
    secret_reference_id: str | None = None
    read_only: bool = True


@dataclass(frozen=True)
class AdapterResult:
    status: str
    data: Any
    warnings: tuple[str, ...] = ()
    retry_after_seconds: int | None = None


class InfrastructureAdapter(ABC):
    """Common boundary for read-only infrastructure integrations.

    Implementations receive only a secret reference. Secret resolution belongs to a
    dedicated runtime provider and raw values must never be returned from these methods.
    """

    adapter_type: str
    capabilities: tuple[str, ...]

    @abstractmethod
    def authenticate(self, context: AdapterContext) -> AdapterResult: ...

    @abstractmethod
    def test_connection(self, context: AdapterContext) -> AdapterResult: ...

    @abstractmethod
    def discover(self, context: AdapterContext) -> AdapterResult: ...

    @abstractmethod
    def collect_inventory(self, context: AdapterContext) -> AdapterResult: ...

    @abstractmethod
    def collect_metrics(self, context: AdapterContext) -> AdapterResult: ...

    @abstractmethod
    def collect_events(self, context: AdapterContext) -> AdapterResult: ...

    @abstractmethod
    def get_health(self, context: AdapterContext) -> AdapterResult: ...

    @abstractmethod
    def get_topology(self, context: AdapterContext) -> AdapterResult: ...

    @abstractmethod
    def normalize(self, payload: Any) -> dict[str, Any]: ...

    @abstractmethod
    def map_assets(self, inventory: list[dict[str, Any]]) -> AdapterResult: ...

    @abstractmethod
    def handle_rate_limit(self, retry_after_seconds: int | None) -> None: ...

    @abstractmethod
    def handle_retry(self, attempt: int, error: Exception) -> None: ...

    @abstractmethod
    def audit(self, context: AdapterContext, action: str, details: dict[str, Any]) -> None: ...


ADAPTER_CATALOG = (
    {
        "adapter_type": "snmp",
        "name": "SNMP",
        "description": "Inventário e telemetria somente leitura por perfis v2c/v3.",
        "capabilities": ["inventory", "metrics", "health", "topology", "discovery"],
        "read_only": True,
        "implemented": False,
    },
    {
        "adapter_type": "unifi",
        "name": "UniFi Controller",
        "description": "Inventário, clientes, APs e topologia via API do controlador.",
        "capabilities": ["inventory", "metrics", "events", "health", "topology"],
        "read_only": True,
        "implemented": False,
    },
    {
        "adapter_type": "fortigate",
        "name": "FortiGate",
        "description": "Inventário, saúde e eventos via acesso de leitura.",
        "capabilities": ["inventory", "metrics", "events", "health", "topology"],
        "read_only": True,
        "implemented": False,
    },
    {
        "adapter_type": "syslog",
        "name": "Syslog",
        "description": "Receiver assíncrono com normalização e rate limit.",
        "capabilities": ["events"],
        "read_only": True,
        "implemented": False,
    },
    {
        "adapter_type": "generic_webhook",
        "name": "Webhook genérico",
        "description": "Recepção de eventos no contrato canônico Vulcan.",
        "capabilities": ["events"],
        "read_only": True,
        "implemented": True,
    },
)
