from __future__ import annotations

import json
from typing import Any, Protocol

from app.config import Settings, get_settings


SYSTEM_INSTRUCTIONS = """
You are Vulcan Insights, the AI analysis layer for an operational intelligence SaaS.
Use only the structured operational facts provided by the application.
Do not infer surveillance, discipline, espionage, or private behavior.
Focus on bottlenecks, inefficiencies, process improvement, automation opportunities,
rework reduction, and data-backed recommendations.
Return concise, explainable recommendations with traceable reasoning.
""".strip()


class InsightClient(Protocol):
    def generate(self, evidence: dict[str, Any]) -> str: ...


class LLMConfigurationError(RuntimeError):
    pass


class OpenAIInsightClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def generate(self, evidence: dict[str, Any]) -> str:
        if self._settings.ai_provider != "openai":
            raise LLMConfigurationError("AI_PROVIDER must be 'openai' for GPT integration")

        if not self._settings.openai_api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is required to generate Vulcan insights")

        from openai import OpenAI

        client = OpenAI(
            api_key=self._settings.openai_api_key,
            organization=self._settings.openai_org_id,
            project=self._settings.openai_project_id,
            timeout=self._settings.openai_timeout_seconds,
        )
        response = client.responses.create(
            model=self._settings.ai_complex_model,
            instructions=SYSTEM_INSTRUCTIONS,
            input=json.dumps(evidence, sort_keys=True, default=str),
            max_output_tokens=self._settings.openai_max_output_tokens,
        )
        return response.output_text


class LlamaOperationalClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def generate(self, evidence: dict[str, Any]) -> str:
        if not self._settings.llama_base_url:
            return (
                "Llama operational pre-analysis is configured as a mock because "
                "LLAMA_BASE_URL is not available. Vulcan would classify events, group "
                "application windows and summarize recurring operational patterns here."
            )

        from openai import OpenAI

        client = OpenAI(
            api_key=self._settings.llama_api_key or "local-llama",
            base_url=self._settings.llama_base_url,
            timeout=self._settings.openai_timeout_seconds,
        )
        response = client.responses.create(
            model=self._settings.llama_model,
            instructions=(
                "You are Vulcan Operational Classifier. Classify and summarize structured "
                "operational facts cheaply. Do not produce executive prose."
            ),
            input=json.dumps(evidence, sort_keys=True, default=str),
            max_output_tokens=min(self._settings.openai_max_output_tokens, 900),
        )
        return response.output_text


class HybridInsightRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._gpt = OpenAIInsightClient(self._settings)
        self._llama = LlamaOperationalClient(self._settings)

    def generate(self, evidence: dict[str, Any]) -> str:
        complexity = evidence.get("complexity", "executive")
        if complexity == "operational":
            return self._llama.generate(evidence)
        return self._gpt.generate(evidence)
