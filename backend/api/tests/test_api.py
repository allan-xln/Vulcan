import os

from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_PROVIDER", "supabase")
os.environ.setdefault("MOCK_AUTH", "true")
os.environ.setdefault("MOCK_DATA", "true")

from app.main import app


client = TestClient(app)


def test_local_admin_login_and_protected_metrics() -> None:
    login_response = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert login_response.status_code == 200
    token = login_response.json()["accessToken"]

    metrics_response = client.get("/metrics", headers={"Authorization": f"Bearer {token}"})
    assert metrics_response.status_code == 200
    assert len(metrics_response.json()) >= 1


def test_local_test_user_login_and_protected_metrics() -> None:
    login_response = client.post("/auth/login", json={"username": "teste", "password": "teste"})
    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["user"]["name"] == "teste"

    metrics_response = client.get("/metrics", headers={"Authorization": f"Bearer {payload['accessToken']}"})
    assert metrics_response.status_code == 200
    assert len(metrics_response.json()) >= 1


def test_operational_intelligence_contract_is_available() -> None:
    token = client.post("/auth/login", json={"username": "teste", "password": "teste"}).json()["accessToken"]
    response = client.get("/operational-intelligence", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert "currentActivity" in payload
    assert "totalActiveSeconds" in payload
    assert "totalIdleSeconds" in payload
    assert "contextSwitchesPerHour" in payload
    assert "distractionScore" in payload
    assert "topApps" in payload
    assert "aiRecommendations" in payload


def test_protected_endpoint_rejects_missing_token() -> None:
    response = client.get("/metrics")

    assert response.status_code == 401


def test_ai_analyze_routes_operational_to_llama() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    response = client.post(
        "/ai/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "tenantId": "00000000-0000-0000-0000-000000000301",
            "complexity": "operational",
            "facts": [{"metric": "context_switches", "value": 420}],
        },
    )

    assert response.status_code == 200
    assert response.json()["route"] == "llama"


def test_hierarchy_returns_dynamic_tree_nodes() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    response = client.get("/hierarchy", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    nodes = response.json()
    assert len(nodes) >= 3
    assert nodes[0]["visibleScope"] in {"self", "subtree", "tenant", "global"}


def test_supabase_status_is_available() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    response = client.get("/supabase/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert "requiredItems" in response.json()


def test_integration_status_endpoints_are_available() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    whatsapp_response = client.get("/integrations/whatsapp/status", headers=headers)
    email_response = client.get("/integrations/email/status", headers=headers)
    combined_response = client.get("/integrations/status", headers=headers)

    assert whatsapp_response.status_code == 200
    assert "rootChannelEnabled" in whatsapp_response.json()
    assert email_response.status_code == 200
    assert len(email_response.json()) >= 1
    assert combined_response.status_code == 200
    assert len(combined_response.json()) >= 2


def test_mock_connection_tests_return_clear_status() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"tenantId": "00000000-0000-0000-0000-000000000301", "message": "Teste automatizado"}

    whatsapp_response = client.post("/integrations/whatsapp/test", headers=headers, json=payload)
    email_response = client.post("/integrations/email/test", headers=headers, json={**payload, "provider": "smtp"})

    assert whatsapp_response.status_code == 200
    assert "providerResult" in whatsapp_response.json()
    assert email_response.status_code == 200
    assert "providerResult" in email_response.json()


def test_schedules_and_report_templates_are_available() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    schedules_response = client.get("/notifications/schedules", headers=headers)
    reports_response = client.get("/reports/templates", headers=headers)

    assert schedules_response.status_code == 200
    assert any(item["recurrence"] == "Imediatamente" for item in schedules_response.json())
    assert reports_response.status_code == 200
    assert any(item["name"] == "Resumo Operacional Diário" for item in reports_response.json())


def test_agent_accepts_rich_operational_events() -> None:
    payload = {
        "tenantId": "00000000-0000-0000-0000-000000000301",
        "enrollmentToken": "vulcan-local-enrollment-token",
        "deviceId": "00000000-0000-0000-0000-000000500001",
        "membershipId": "00000000-0000-0000-0000-000000300005",
        "machineFingerprint": "test-rich-agent-fingerprint",
        "hostname": "pytest-agent",
        "events": [
            {
                "eventId": "rich-event-1",
                "eventType": "context_switch",
                "appName": "Troca de contexto",
                "startedAt": "2026-06-07T04:00:00Z",
                "endedAt": "2026-06-07T04:00:00Z",
                "durationSeconds": 0,
                "metadata": {"fromApp": "ERP", "toApp": "Navegador", "quality": "high"},
            },
            {
                "eventId": "rich-event-2",
                "eventType": "idle_ended",
                "appName": "Sistema",
                "startedAt": "2026-06-07T04:01:00Z",
                "endedAt": "2026-06-07T04:06:00Z",
                "durationSeconds": 300,
                "metadata": {"quality": "high"},
            },
        ],
    }

    response = client.post("/agent/events", json=payload)

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["received"] == 2
