from uuid import UUID

from app.main import InsightRequest, explain_operational_facts, health


class FakeInsightClient:
    def __init__(self) -> None:
        self.evidence = None

    def generate(self, evidence):
        self.evidence = evidence
        return "Prioritize reducing queue depth in the finance workflow."


def test_health_endpoint() -> None:
    response = health()

    assert response.status == "ok"
    assert response.service == "ai-api"
    assert response.truth_model == "structured-data-only"
    assert response.llm_provider in {"openai", "hybrid"}
    assert response.complex_model
    assert response.operational_model


def test_explain_operational_facts_uses_structured_evidence_only() -> None:
    client = FakeInsightClient()
    request = InsightRequest(
        tenantId=UUID("00000000-0000-0000-0000-000000000301"),
        question="Where is the bottleneck?",
        facts=[
            {
                "metric": "queue_depth",
                "workflow": "finance",
                "value": 12,
            }
        ],
    )

    response = explain_operational_facts(request=request, client=client)

    assert response.insight == "Prioritize reducing queue depth in the finance workflow."
    assert client.evidence["tenantId"] == "00000000-0000-0000-0000-000000000301"
    assert client.evidence["guardrails"]["purpose"] == "operational intelligence"
