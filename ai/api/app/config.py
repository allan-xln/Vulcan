from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    ai_provider: str
    openai_api_key: str | None
    openai_org_id: str | None
    openai_project_id: str | None
    openai_model: str
    openai_timeout_seconds: float
    openai_max_output_tokens: int
    ai_complex_model: str
    ai_operational_model: str
    llama_provider: str
    llama_base_url: str | None
    llama_api_key: str | None
    llama_model: str


def get_settings() -> Settings:
    return Settings(
        ai_provider=getenv("AI_PROVIDER", "openai"),
        openai_api_key=getenv("OPENAI_API_KEY") or None,
        openai_org_id=getenv("OPENAI_ORG_ID") or None,
        openai_project_id=getenv("OPENAI_PROJECT_ID") or None,
        openai_model=getenv("OPENAI_MODEL", "gpt-5.5"),
        openai_timeout_seconds=float(getenv("OPENAI_TIMEOUT_SECONDS", "60")),
        openai_max_output_tokens=int(getenv("OPENAI_MAX_OUTPUT_TOKENS", "2000")),
        ai_complex_model=getenv("AI_COMPLEX_MODEL", getenv("OPENAI_MODEL", "gpt-5.5")),
        ai_operational_model=getenv("AI_OPERATIONAL_MODEL", getenv("LLAMA_MODEL", "llama-4-maverick")),
        llama_provider=getenv("LLAMA_PROVIDER", "openai-compatible"),
        llama_base_url=getenv("LLAMA_BASE_URL") or None,
        llama_api_key=getenv("LLAMA_API_KEY") or getenv("OPENAI_API_KEY") or None,
        llama_model=getenv("LLAMA_MODEL", "llama-4-maverick"),
    )
