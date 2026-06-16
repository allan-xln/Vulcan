# Configuration

Este documento resume como o Vulcan carrega configuracoes.

## Fontes

1. Variaveis de ambiente: infraestrutura, secrets e providers globais.
2. `tenant_settings`: defaults e politicas por tenant.
3. Tabelas de dominio: usuarios, equipes, hierarquia, notificacoes e dispositivos.

## Regra De Secrets

Secrets nunca voltam para o frontend:

- database password;
- service role key;
- OpenAI key;
- Llama/OpenRouter/Groq key;
- SMTP password;
- WhatsApp token;
- OAuth refresh token.

O frontend recebe apenas status: `configurado`, `requer credencial`, `mock explicito` ou `erro`.

## Validacao

O backend valida:

- secao conhecida;
- campo conhecido;
- campo editavel;
- tipo do valor;
- required;
- pesos de metricas somando 100%;
- politica segura de coleta.

## Auditoria

Toda chamada `PUT /settings/{section}` registra:

- tenant;
- usuario quando disponivel;
- secao;
- chaves alteradas;
- horario;
- recurso `tenant_settings`.

## Variaveis Relacionadas

- `DATABASE_URL`
- `AUTH_PROVIDER`
- `API_ALLOWED_ORIGINS`
- `API_ALLOWED_ORIGIN_REGEX`
- `OPENAI_API_KEY`
- `LLAMA_BASE_URL`
- `SMTP_HOST`
- `SMTP_PASS`
- `ROOT_WHATSAPP_NUMBER`
- `WHATSAPP_ACCESS_TOKEN`
- `AGENT_ENROLLMENT_TOKEN`
