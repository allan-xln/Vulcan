from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.infrastructure_sync import InfrastructureSyncService


def service_with_settings(**overrides) -> InfrastructureSyncService:
    settings = {
        "unifi_base_url": "",
        "unifi_username": "",
        "unifi_password": "",
        "unifi_site": "default",
        "unifi_verify_tls": True,
        "proxmox_base_url": "",
        "proxmox_username": "",
        "proxmox_password": "",
        "proxmox_verify_tls": True,
    }
    settings.update(overrides)
    service = object.__new__(InfrastructureSyncService)
    service.settings = SimpleNamespace(**settings)
    service.repository = SimpleNamespace(enabled=True)
    return service


def test_unifi_sync_fails_closed_without_runtime_credentials() -> None:
    result = service_with_settings().sync_unifi(uuid4())

    assert result.adapter_type == "unifi"
    assert result.status == "unavailable"
    assert result.data_origin == "real"
    assert result.assets_seen == 0
    assert result.warnings == ["Credencial runtime da UniFi não configurada."]


def test_proxmox_sync_fails_closed_without_runtime_credentials() -> None:
    result = service_with_settings().sync_proxmox(uuid4())

    assert result.adapter_type == "proxmox"
    assert result.status == "unavailable"
    assert result.data_origin == "real"
    assert result.assets_seen == 0
    assert result.warnings == ["Credencial runtime do Proxmox não configurada."]


def test_sync_rejects_unsupported_adapter_before_any_network_request() -> None:
    service = service_with_settings()

    with pytest.raises(ValueError, match="unsupported infrastructure adapter"):
        service.sync(uuid4(), "fortigate")


def test_sync_requires_database_before_adapter_dispatch() -> None:
    service = service_with_settings()
    service.repository.enabled = False

    with pytest.raises(ValueError, match="database is required"):
        service.sync(uuid4(), "unifi")
