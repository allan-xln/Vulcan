# Configuration

Este documento resume como o Vulcan carrega configuracoes.

## Fontes

1. Variaveis de ambiente: infraestrutura, secrets e providers globais.
2. `tenant_settings`: defaults e politicas por tenant.
3. Tabelas de dominio: usuarios, equipes, hierarquia, notificacoes e dispositivos.
4. Runtime store local `.runtime/integration-secrets.json` para configuracoes de integracao salvas pela tela em ambiente local/piloto.

## Regra De Secrets

Secrets nunca voltam para o frontend:

- database password;
- service role key;
- OpenAI key;
- Llama/OpenRouter/Groq key;
- SMTP password;
- WhatsApp token;
- Evolution API key;
- Evolution webhook token;
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
- `ROOT_WHATSAPP_PROVIDER`
- `ROOT_WHATSAPP_MOCK_MODE`
- `EVOLUTION_ENABLED`
- `EVOLUTION_BASE_URL`
- `EVOLUTION_API_KEY`
- `EVOLUTION_INSTANCE_NAME`
- `EVOLUTION_WEBHOOK_URL`
- `EVOLUTION_WEBHOOK_TOKEN`
- `WHATSAPP_PROVIDER`
- `WHATSAPP_REQUIRE_OPT_IN`
- `WHATSAPP_ENABLE_UNOFFICIAL_PROVIDER`
- `WHATSAPP_EMAIL_FALLBACK_ENABLED`
- `WHATSAPP_IN_APP_FALLBACK_ENABLED`
- `WHATSAPP_ACCESS_TOKEN`
- `AGENT_ENROLLMENT_TOKEN`

## WhatsApp Evolution Runtime

`PUT /integrations/whatsapp/evolution/config` salva configuracoes locais quando `ALLOW_RUNTIME_INTEGRATION_CONFIG=true`. Em producao, use cofre/variaveis do deploy e mantenha runtime config desabilitado.

O frontend nunca recebe o valor real da API key; recebe apenas `apiKeyConfigured=true/false`.
