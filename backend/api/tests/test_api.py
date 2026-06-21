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


def test_cors_allows_dynamic_localhost_ports_and_blocks_unknown_origins() -> None:
    allowed_response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://127.0.0.1:3012",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert allowed_response.status_code == 200
    assert allowed_response.headers["access-control-allow-origin"] == "http://127.0.0.1:3012"

    commercial_response = client.options(
        "/auth/login",
        headers={
            "Origin": "https://vulcan.lanfuture.dev",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert commercial_response.status_code == 200
    assert commercial_response.headers["access-control-allow-origin"] == "https://vulcan.lanfuture.dev"

    blocked_response = client.options(
        "/auth/login",
        headers={
            "Origin": "https://malicioso.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert blocked_response.status_code == 400


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


def test_teams_and_pending_adoption_contracts_are_available() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    teams_response = client.get("/teams", headers=headers)
    pending_response = client.get("/devices/pending-adoption", headers=headers)

    assert teams_response.status_code == 200
    assert any(item["name"] == "Financeiro" for item in teams_response.json())
    assert pending_response.status_code == 200
    pending_devices = pending_response.json()
    assert len(pending_devices) >= 1
    assert pending_devices[0]["adoptionStatus"] == "pending"


def test_mock_device_adoption_and_metrics_export_contracts() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}
    device_id = "00000000-0000-0000-0000-000000000901"

    adoption_response = client.post(
        f"/devices/{device_id}/adopt",
        headers=headers,
        json={
            "tenantId": "00000000-0000-0000-0000-000000000301",
            "mode": "dry",
            "policy": "standard",
        },
    )
    detailed_response = client.get("/metrics/detailed?period=24h", headers=headers)
    export_response = client.get("/metrics/export?format=csv&period=24h", headers=headers)

    assert adoption_response.status_code == 200
    assert adoption_response.json()["adopted"] is True
    assert adoption_response.json()["device"]["adoptionStatus"] == "adopted"
    assert detailed_response.status_code == 200
    assert export_response.status_code == 200
    assert "data_hora,usuario,equipe" in export_response.text


def test_supabase_status_is_available() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    response = client.get("/supabase/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert "requiredItems" in response.json()
    assert "databaseReachable" in response.json()


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


def test_settings_center_loads_saves_and_validates() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    settings_response = client.get("/settings", headers=headers)
    assert settings_response.status_code == 200
    payload = settings_response.json()
    assert payload["summary"]["totalSections"] >= 8
    assert any(section["id"] == "company" for section in payload["sections"])
    assert any(field["isSecret"] for section in payload["sections"] for field in section["fields"])

    save_response = client.put(
        "/settings/company",
        headers=headers,
        json={"values": {"displayName": "Vulcan QA", "slug": "vulcan-qa", "timezone": "America/Sao_Paulo", "language": "pt-BR"}},
    )
    assert save_response.status_code == 200
    assert save_response.json()["saved"] is True

    invalid_response = client.put(
        "/settings/metrics",
        headers=headers,
        json={"values": {"weightAgents": 1, "weightFocus": 1, "weightIdle": 1, "weightContext": 1, "weightBottlenecks": 1}},
    )
    assert invalid_response.status_code == 400
    assert "100%" in invalid_response.json()["detail"]

    test_response = client.post("/settings/ai/test", headers=headers)
    assert test_response.status_code == 200
    assert test_response.json()["tested"] is True


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


def test_root_whatsapp_channel_contracts_are_available() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    recipients_response = client.get(
        "/integrations/whatsapp/root/recipients?notificationType=alerta&audience=managers",
        headers=headers,
    )
    dry_run_response = client.post(
        "/integrations/whatsapp/root/send",
        headers=headers,
        json={
            "tenantId": "00000000-0000-0000-0000-000000000301",
            "notificationType": "alerta",
            "title": "Alerta de QA",
            "message": "Mensagem controlada de QA.",
            "audience": "managers",
            "priority": "alto",
            "dryRun": True,
        },
    )

    assert recipients_response.status_code == 200
    assert len(recipients_response.json()) >= 1
    assert recipients_response.json()[0]["whatsapp"]
    assert dry_run_response.status_code == 200
    payload = dry_run_response.json()
    assert payload["mode"] in {"mock", "missing_credentials", "connected", "disabled"}
    assert payload["mocked"] >= 1
    assert payload["queued"] == 0


def test_evolution_whatsapp_contracts_are_available_and_protected() -> None:
    token = client.post("/auth/login", json={"username": "admin", "password": "admin"}).json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}
    tenant_token = client.post("/auth/login", json={"username": "teste", "password": "teste"}).json()["accessToken"]
    tenant_headers = {"Authorization": f"Bearer {tenant_token}"}

    status_response = client.get("/integrations/whatsapp/evolution/status", headers=headers)
    tenant_status_response = client.get("/integrations/whatsapp/evolution/status", headers=tenant_headers)
    tenant_public_status_response = client.get("/integrations/whatsapp/status", headers=tenant_headers)
    tenant_queue_response = client.get("/integrations/whatsapp/root/queue", headers=tenant_headers)
    qr_response = client.get("/integrations/whatsapp/evolution/qr", headers=headers)
    send_test_response = client.post(
        "/integrations/whatsapp/evolution/send-test",
        headers=headers,
        json={
            "tenantId": "00000000-0000-0000-0000-000000000301",
            "provider": "evolution",
            "destination": "5541999999999",
            "message": "Teste automatizado",
        },
    )
    invalid_config_response = client.put(
        "/integrations/whatsapp/evolution/config",
        headers=headers,
        json={
            "enabled": True,
            "provider": "evolution",
            "rootNumber": "",
            "rootName": "Vulcan QA",
            "baseUrl": "http://127.0.0.1:8080",
            "instanceName": "vulcan-root",
            "mockMode": False,
            "requireOptIn": True,
            "emailFallbackEnabled": True,
            "inAppFallbackEnabled": True,
        },
    )
    webhook_response = client.post("/integrations/whatsapp/evolution/webhook", json={"event": "CONNECTION_UPDATE"})

    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["provider"]
    assert status_payload["status"] in {
        "disabled",
        "mock",
        "missing_credentials",
        "unofficial_disconnected",
        "unofficial_qr_required",
        "unofficial_connected",
        "unofficial_failed",
        "unofficial_rate_limited",
        "official_ready_future",
    }
    assert "apiKeyConfigured" in status_payload
    assert "mockMode" in status_payload
    assert tenant_status_response.status_code == 403
    assert tenant_public_status_response.status_code == 200
    assert tenant_public_status_response.json()["provider"] == "vulcan_managed"
    assert tenant_public_status_response.json()["qrCode"] is None
    assert tenant_public_status_response.json()["logs"] == []
    assert tenant_queue_response.status_code == 403
    assert qr_response.status_code == 200
    assert "status" in qr_response.json()
    assert send_test_response.status_code == 200
    assert "providerResult" in send_test_response.json()
    assert invalid_config_response.status_code == 422
    assert webhook_response.status_code == 401


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
