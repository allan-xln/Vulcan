from app.main import health


def test_health_endpoint() -> None:
    response = health()

    assert response.status == "ok"
    assert response.service == "ai-api"
    assert response.truth_model == "structured-data-only"
