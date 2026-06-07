from __future__ import annotations

from app.config import Settings, get_settings
from app.schemas import AnalyzeRequest, AnalyzeResponse, CopilotRequest, CopilotResponse


def analyze_facts(request: AnalyzeRequest, settings: Settings | None = None) -> AnalyzeResponse:
    settings = settings or get_settings()
    use_gpt = request.complexity in {"executive", "critical"}
    route = "gpt" if use_gpt else "llama"
    model = settings.ai_complex_model if use_gpt else settings.ai_operational_model

    focus = "gargalos críticos e recomendações executivas" if use_gpt else "padrões operacionais recorrentes"
    return AnalyzeResponse(
        route=route,
        model=model,
        summary=f"Vulcan analisou {len(request.facts)} fatos estruturados e priorizou {focus}.",
        recommendations=[
            "Agrupar eventos por fluxo operacional antes de gerar insights executivos.",
            "Enviar ao GPT apenas casos de alto impacto ou diagnósticos complexos.",
            "Usar Llama para classificação recorrente, agrupamento e pré-análise de baixo custo.",
        ],
    )


def answer_copilot(request: CopilotRequest, settings: Settings | None = None) -> CopilotResponse:
    settings = settings or get_settings()
    return CopilotResponse(
        route="gpt",
        model=settings.ai_complex_model,
        answer=(
            "Vulcan Copilot está preparado para responder com base em dados operacionais "
            "do tenant ativo. Para produção, este endpoint deve chamar a AI API com "
            "fatos estruturados, filtros de tenant e trilha de auditoria."
        ),
    )
