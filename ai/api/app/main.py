from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.llm import HybridInsightRouter, InsightClient, LLMConfigurationError


class HealthResponse(BaseModel):
    status: str
    service: str
    truth_model: str
    llm_provider: str
    llm_configured: bool
    complex_model: str
    operational_model: str


class InsightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    question: str | None = Field(default=None, max_length=1000)
    facts: list[dict[str, Any]] = Field(min_length=1, max_length=200)
    complexity: str = Field(default="executive", pattern="^(operational|executive|critical)$")


class InsightResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    tenant_id: UUID = Field(alias="tenantId")
    provider: str
    model: str
    insight: str


app = FastAPI(title="Vulcan AI API", version="0.1.0")


def get_insight_client() -> InsightClient:
    return HybridInsightRouter()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="ai-api",
        truth_model="structured-data-only",
        llm_provider=settings.ai_provider,
        llm_configured=settings.openai_api_key is not None,
        complex_model=settings.ai_complex_model,
        operational_model=settings.ai_operational_model,
    )


@app.post("/v1/insights/explain", response_model=InsightResponse)
def explain_operational_facts(
    request: InsightRequest,
    client: InsightClient = Depends(get_insight_client),
) -> InsightResponse:
    settings = get_settings()
    evidence = {
        "tenantId": str(request.tenant_id),
        "question": request.question,
        "complexity": request.complexity,
        "facts": request.facts,
        "guardrails": {
            "purpose": "operational intelligence",
            "forbiddenUses": ["surveillance", "espionage", "password capture", "keystroke capture"],
        },
    }

    try:
        insight = client.generate(evidence)
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return InsightResponse(
        tenantId=request.tenant_id,
        provider=settings.ai_provider,
        model=settings.openai_model,
        insight=insight,
    )
