# AI

## Hybrid AI Provider

Vulcan uses a hybrid AI architecture:

- GPT through OpenAI for complex, executive, strategic, and high-impact work.
- Llama through Ollama, OpenRouter, Together, Groq, or another OpenAI-compatible provider for operational, repetitive, lower-cost processing.

The dedicated AI service is `ai/api`. The local SaaS API also exposes `/ai/analyze` and `/ai/copilot` so the frontend can work with clean mocks while production providers are finalized.

## Official Model Defaults

- Complex model: `gpt-5.5`.
- Operational model: `llama-4-maverick`.

OpenAI's current model documentation recommends `gpt-5.5` for complex reasoning and professional work. Meta's official Llama 4 release made Llama 4 Scout and Llama 4 Maverick available publicly; Vulcan uses Maverick as the preferred operational model because it is the higher-capacity released Llama 4 option, with Scout kept as a possible long-context/cost fallback.

## Required Environment

```env
AI_PROVIDER=hybrid
OPENAI_API_KEY=replace-me
OPENAI_MODEL=gpt-5.5
AI_COMPLEX_MODEL=gpt-5.5
AI_OPERATIONAL_MODEL=llama-4-maverick
OPENAI_TIMEOUT_SECONDS=60
OPENAI_MAX_OUTPUT_TOKENS=2000
OPENAI_ORG_ID=
OPENAI_PROJECT_ID=

LLAMA_PROVIDER=ollama
LLAMA_BASE_URL=http://localhost:11434/v1
LLAMA_MODEL=llama-4-maverick
LLAMA_API_KEY=
```

`OPENAI_ORG_ID`, `OPENAI_PROJECT_ID`, and `LLAMA_API_KEY` are optional unless the chosen provider requires them.

## AI Flow

Raw operational events -> Supabase PostgreSQL -> internal rules -> Llama classification and pre-analysis -> metrics -> GPT executive analysis for relevant complex cases -> Vulcan dashboard -> Windows, WhatsApp, push and email notifications.

## Llama Providers

The provider abstraction must support:

- `ollama`: local/private runtime, best for development and private deployments.
- `openrouter`: hosted routing across Llama variants.
- `together`: hosted Llama inference.
- `groq`: low-latency hosted inference.
- `openai-compatible`: generic fallback for any compatible API.

## GPT Responsibilities

- Executive analysis.
- Strategic recommendations.
- Vulcan Copilot answers.
- Complex bottleneck diagnosis.
- High-impact automation suggestions.
- Premium narrative summaries for managers.
- Weekly and monthly management reports.

## Llama Responsibilities

- Event classification.
- Application and window categorization.
- Operational grouping.
- Simple summaries.
- Batch pre-analysis.
- Basic alert generation.
- First-pass pattern detection.
- Cost reduction before GPT escalation.

## Current Endpoints

- `GET /health`
- `POST /v1/insights/explain`
- `GET /ai/status` in `backend/api`
- `POST /ai/analyze` in `backend/api`
- `POST /ai/insights/generate` in `backend/api`
- `POST /ai/copilot` in `backend/api`

The explain endpoint accepts tenant-scoped structured facts and returns operational recommendations. When credentials are missing, services return explicit mock responses instead of silently pretending that production AI is active.

## Ollama Local Runtime

Recommended local commands for the operational Llama layer:

```bash
ollama serve
ollama pull llama3.1
```

Then set:

```env
LLAMA_PROVIDER=ollama
LLAMA_BASE_URL=http://localhost:11434/v1
LLAMA_MODEL=llama3.1
```

Use hosted providers by pointing `LLAMA_BASE_URL` and `LLAMA_API_KEY` to OpenRouter, Together, Groq, or another OpenAI-compatible endpoint.

## Product Modules

Vulcan Insights:
Explain bottlenecks, inefficiencies, rework patterns, and automation opportunities.

Vulcan Copilot:
Conversational assistant over tenant-scoped operational data.

Vulcan Vision:
Future visual analytics layer for charts, dashboards, and operational flow interpretation. It must not become screenshot surveillance.

Vulcan Automation:
Recommendation-to-workflow engine for automation candidates.

Vulcan Benchmark:
Aggregated and anonymized benchmark intelligence across tenants, only after privacy, consent, anonymization, and contractual controls are implemented.
