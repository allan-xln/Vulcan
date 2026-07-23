import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_PROVIDER", "supabase")
os.environ.setdefault("MOCK_AUTH", "true")
os.environ.setdefault("MOCK_DATA", "true")
os.environ.setdefault("NEXT_PUBLIC_ENVIRONMENT", "local")

from app.main import app
from app.platform_repository import PlatformAuthorizationError, PlatformRepository
from app.repository import AccessScope
from app.security import AuthContext


client = TestClient(app)
TENANT_ID = "00000000-0000-0000-0000-000000000301"
FOREIGN_TENANT_ID = "00000000-0000-0000-0000-000000000999"


def admin_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    return {
        "Authorization": f"Bearer {response.json()['accessToken']}",
        "X-Tenant-Id": TENANT_ID,
    }


def operator_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "operador1", "password": "operador1"})
    assert response.status_code == 200
    return {
        "Authorization": f"Bearer {response.json()['accessToken']}",
        "X-Tenant-Id": TENANT_ID,
    }


def test_platform_health_liveness_readiness_and_version() -> None:
    health = client.get("/healthz")
    live = client.get("/livez")
    ready = client.get("/readyz")
    version = client.get("/version")

    assert health.status_code == 200
    assert health.json()["dataOrigin"] == "simulated"
    assert live.status_code == 200
    assert live.json()["checks"][0]["name"] == "process"
    assert ready.status_code == 200
    assert version.status_code == 200
    assert version.json()["eventSchemaVersion"] == "2026-07-vulcan-event.v1"


def test_platform_modules_keep_workforce_enabled_and_infrastructure_separate() -> None:
    response = client.get("/platform/modules", headers=admin_headers())

    assert response.status_code == 200
    modules = {item["moduleKey"]: item["enabled"] for item in response.json()}
    assert modules["workforce"] is True
    assert modules["infrastructure"] is True
    assert modules["timeline"] is True
    assert modules["security"] is False


def test_infrastructure_overview_and_inventory_are_explicitly_simulated() -> None:
    headers = admin_headers()
    overview = client.get("/infrastructure/overview", headers=headers)
    sites = client.get("/infrastructure/sites", headers=headers)
    networks = client.get("/infrastructure/networks", headers=headers)
    assets = client.get("/infrastructure/assets", headers=headers)

    assert overview.status_code == 200
    assert overview.json()["dataOrigin"] == "simulated"
    assert overview.json()["scoreComponents"][0]["formula"]
    assert sites.status_code == 200
    assert sites.json()[0]["dataOrigin"] == "simulated"
    assert networks.status_code == 200
    assert networks.json()[0]["discoveryAllowed"] is False
    assert assets.status_code == 200
    assert assets.json()[0]["source"] == "simulator"


def test_admin_can_use_site_network_and_asset_create_contracts_in_mock_mode() -> None:
    headers = admin_headers()
    site = client.post(
        "/infrastructure/sites",
        headers=headers,
        json={
            "tenantId": TENANT_ID,
            "code": "QA-SITE",
            "name": "Site QA",
            "timezone": "America/Sao_Paulo",
        },
    )
    assert site.status_code == 201
    assert site.json()["dataOrigin"] == "simulated"

    network = client.post(
        "/infrastructure/networks",
        headers=headers,
        json={
            "tenantId": TENANT_ID,
            "siteId": site.json()["id"],
            "name": "Rede QA",
            "networkCidr": "10.77.0.0/24",
            "gateway": "10.77.0.1",
            "discoveryAllowed": False,
        },
    )
    assert network.status_code == 201
    assert network.json()["networkCidr"] == "10.77.0.0/24"

    asset = client.post(
        "/infrastructure/assets",
        headers=headers,
        json={
            "tenantId": TENANT_ID,
            "siteId": site.json()["id"],
            "networkId": network.json()["id"],
            "assetType": "server",
            "name": "Servidor QA",
            "hostname": "QA-SRV-01",
            "ipAddress": "10.77.0.10",
            "status": "unknown",
            "criticality": "high",
        },
    )
    assert asset.status_code == 201
    assert asset.json()["assetType"] == "server"
    assert asset.json()["dataOrigin"] == "simulated"


def test_foreign_tenant_write_is_rejected_even_for_local_admin() -> None:
    response = client.post(
        "/infrastructure/sites",
        headers=admin_headers(),
        json={
            "tenantId": FOREIGN_TENANT_ID,
            "code": "FOREIGN",
            "name": "Tenant estrangeiro",
        },
    )

    assert response.status_code == 400
    assert "tenant" in response.json()["detail"]


def test_read_only_workforce_user_cannot_mutate_infrastructure() -> None:
    write_response = client.post(
        "/infrastructure/sites",
        headers=operator_headers(),
        json={
            "tenantId": TENANT_ID,
            "code": "DENIED",
            "name": "Mutação negada",
        },
    )

    read_response = client.get("/infrastructure/overview", headers=operator_headers())
    timeline_response = client.get("/timeline", headers=operator_headers())

    assert write_response.status_code == 403
    assert "permission" in write_response.json()["detail"]
    assert read_response.status_code == 403
    assert "permission" in read_response.json()["detail"]
    assert timeline_response.status_code == 200
    assert timeline_response.json()["items"] == []


def test_tenant_scoped_auditor_is_not_treated_as_an_administrator() -> None:
    access = AccessScope(
        tenant_id=UUID(TENANT_ID),
        user_id="auditor",
        membership_id=None,
        department_id=None,
        scope="tenant",
        is_root=False,
        role_slug="auditor",
    )
    context = AuthContext(
        user_id="auditor",
        email="auditor@vulcan.local",
        tenant_id=UUID(TENANT_ID),
        role="tenant_admin",
        provider="local",
    )

    with pytest.raises(PlatformAuthorizationError):
        PlatformRepository._assert_admin(access, context)


def test_unified_timeline_and_event_simulator_are_explicit() -> None:
    headers = admin_headers()
    timeline = client.get("/timeline?limit=10", headers=headers)
    simulation = client.post(
        "/events/simulate",
        headers=headers,
        json={
            "tenantId": TENANT_ID,
            "scenario": "workforce_infrastructure_impact",
            "count": 4,
        },
    )

    assert timeline.status_code == 200
    assert timeline.json()["dataOrigin"] == "simulated"
    assert timeline.json()["items"][0]["technicalMessage"].startswith("Evento de demonstração")
    assert simulation.status_code == 200
    assert simulation.json()["generated"] == 4
    assert all(item["dataOrigin"] == "simulated" for item in simulation.json()["events"])
    assert {item["category"] for item in simulation.json()["events"]} >= {"workforce", "network"}


def test_canonical_event_contract_accepts_timezone_and_rejects_tenant_mismatch() -> None:
    event_id = str(uuid4())
    payload = {
        "eventId": event_id,
        "tenantId": TENANT_ID,
        "source": "contract-test",
        "sourceType": "test",
        "sourceEventId": event_id,
        "eventType": "test.contract",
        "category": "operational",
        "severity": "info",
        "occurredAt": "2026-07-23T12:00:00-03:00",
        "message": "Evento contratual de teste.",
    }
    accepted = client.post("/events", headers=admin_headers(), json=payload)
    rejected = client.post(
        "/events",
        headers=admin_headers(),
        json={**payload, "eventId": str(uuid4()), "tenantId": FOREIGN_TENANT_ID},
    )

    assert accepted.status_code == 200
    assert accepted.json()["accepted"] is True
    assert accepted.json()["event"]["schemaVersion"] == "2026-07-vulcan-event.v1"
    assert rejected.status_code == 400


def test_discovery_requires_private_allowlist_and_remains_read_only() -> None:
    headers = admin_headers()
    site_id = client.get("/infrastructure/sites", headers=headers).json()[0]["id"]
    public_network = client.post(
        "/infrastructure/discovery/policies",
        headers=headers,
        json={
            "tenantId": TENANT_ID,
            "siteId": site_id,
            "name": "Bloqueada",
            "allowedNetworks": ["8.8.8.0/24"],
            "maxTargets": 256,
        },
    )
    private_network = client.post(
        "/infrastructure/discovery/policies",
        headers=headers,
        json={
            "tenantId": TENANT_ID,
            "siteId": site_id,
            "name": "Privada segura",
            "allowedNetworks": ["10.20.30.0/28"],
            "allowedProtocols": ["icmp", "dns"],
            "maxTargets": 32,
        },
    )

    assert public_network.status_code == 400
    assert "public networks" in public_network.json()["detail"]
    assert private_network.status_code == 201
    assert private_network.json()["readOnly"] is True
    assert private_network.json()["safeMode"] is True
    assert private_network.json()["enabled"] is False

    approved = client.patch(
        f"/infrastructure/discovery/policies/{private_network.json()['id']}",
        headers=headers,
        json={"tenantId": TENANT_ID, "enabled": True},
    )
    rejected_foreign = client.patch(
        f"/infrastructure/discovery/policies/{private_network.json()['id']}",
        headers=headers,
        json={"tenantId": FOREIGN_TENANT_ID, "enabled": True},
    )

    assert approved.status_code == 200
    assert approved.json()["enabled"] is True
    assert approved.json()["readOnly"] is True
    assert rejected_foreign.status_code == 400


def test_integration_catalog_exposes_capabilities_without_fake_connections() -> None:
    response = client.get("/infrastructure/integrations/catalog", headers=admin_headers())

    assert response.status_code == 200
    catalog = response.json()
    assert any(item["adapterType"] == "generic_webhook" and item["implemented"] for item in catalog)
    assert any(item["adapterType"] == "snmp" and not item["implemented"] for item in catalog)
    assert all(item["readOnly"] for item in catalog)
