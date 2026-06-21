# API

## Local SaaS API

Base service: `backend/api`

- `GET /health`
- `POST /auth/login`
- `GET /tenants`
- `GET /departments`
- `GET /roles`
- `GET /memberships`
- `POST /memberships`
- `PUT /memberships/{membership_id}`
- `PUT /memberships/{membership_id}/manager`
- `GET /users`
- `GET /hierarchy`
- `GET /devices`
- `PUT /devices/{device_id}/owner`
- `GET /activity-events`
- `POST /activity-events`
- `GET /metrics`
- `GET /metrics/detailed`
- `GET /metrics/export`
- `GET /operational-metrics`
- `GET /operational-intelligence`
- `GET /insights`
- `GET /insights/{insight_id}`
- `POST /insights/generate`
- `POST /insights/{insight_id}/ask`
- `POST /insights/{insight_id}/send-whatsapp`
- `POST /insights/{insight_id}/send-email`
- `POST /insights/{insight_id}/resolve`
- `POST /insights/{insight_id}/create-action`
- `GET /notifications`
- `GET /notifications/summary`
- `GET /notifications/{notification_id}`
- `POST /notifications/test`
- `POST /notifications/send`
- `POST /notifications/{notification_id}/retry`
- `POST /notifications/{notification_id}/cancel`
- `POST /notifications/{notification_id}/mark-read`
- `POST /notifications/{notification_id}/resolve`
- `GET /notification-types`
- `GET /notifications/preferences`
- `PUT /notifications/preferences/{preference_id}`
- `GET /notifications/schedules`
- `POST /notification-schedules`
- `PUT /notification-schedules/{schedule_id}`
- `DELETE /notification-schedules/{schedule_id}`
- `POST /notification-schedules/{schedule_id}/pause`
- `POST /notification-schedules/{schedule_id}/resume`
- `GET /notification-templates`
- `POST /notification-templates/{template_id}/preview`
- `POST /notification-templates/{template_id}/test`
- `GET /reports/templates`
- `GET /integrations/whatsapp/status`
- `POST /integrations/whatsapp/test`
- `GET /integrations/whatsapp/evolution/status`
- `PUT /integrations/whatsapp/evolution/config`
- `POST /integrations/whatsapp/evolution/test`
- `GET /integrations/whatsapp/evolution/qr`
- `POST /integrations/whatsapp/evolution/reconnect`
- `POST /integrations/whatsapp/evolution/send-test`
- `POST /integrations/whatsapp/evolution/webhook`
- `GET /integrations/whatsapp/root/recipients`
- `POST /integrations/whatsapp/root/send`
- `POST /integrations/whatsapp/root/process-queue`
- `GET /integrations/whatsapp/root/queue`
- `GET /integrations/whatsapp/root/logs`
- `POST /integrations/whatsapp/root/queue/{queue_id}/retry`
- `GET /integrations/email/status`
- `POST /integrations/email/test`
- `GET /integrations/status`
- `GET /settings`
- `GET /settings/summary`
- `GET /settings/{section_id}`
- `PUT /settings/{section_id}`
- `POST /settings/{section_id}/test`
- `POST /settings/{section_id}/reset`
- `GET /ai/status`
- `POST /ai/analyze`
- `POST /ai/insights/generate`
- `POST /ai/copilot`
- `GET /ai-provider-configs`
- `GET /audit-logs`
- `GET /supabase/status`
- `GET /agent/status`
- `POST /agent/enroll`
- `POST /agent/heartbeat`
- `POST /agent/events`
- `POST /agent/sync`
- `POST /agent/logs`

Local protected routes accept:

```text
Authorization: Bearer dev-vulcan-admin-token
```

Production protected routes must validate Supabase Auth JWTs and resolve tenant membership before querying business data.

## CORS

Local development accepts configured origins from:

```env
API_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3002,http://localhost:3102,http://127.0.0.1:3102,https://vulcan.lanfuture.dev,https://vulcan-demo.lanfuture.dev,https://vulcan-staging.lanfuture.dev
API_ALLOWED_ORIGIN_REGEX=^https?://(localhost|127\\.0\\.0\\.1):[0-9]+$
```

`API_ALLOWED_ORIGINS` accepts CSV or a JSON array. `ALLOWED_ORIGINS` is accepted as an alias for deploy platforms. In production, define exact public origins and avoid a broad regex. CORS preflight is covered by backend tests and was manually validated with a dynamic local port.

When deployed on Vercel, `VERCEL_URL` or `NEXT_PUBLIC_VERCEL_URL` is also converted into one exact allowed origin. Broad `*.vercel.app` regexes should stay limited to temporary staging environments.

If PostgreSQL is unreachable, data endpoints return `503 database_unavailable` with a clear message instead of leaking a driver traceback or pretending that mock data is real.

Membership manager changes reject cycles and refresh `membership_closure`. Activity event ingestion persists the event, writes an `operational_metrics` row, and records an audit log.

Agent endpoints are intentionally separated from dashboard auth. They require `enrollmentToken` matching `AGENT_ENROLLMENT_TOKEN`, write tenant-scoped device/activity/metric records, and keep local agent operation independent from a human dashboard session.

Agent sync is idempotent by `eventId`: the backend persists it as `activity_events.source_event_id` with uniqueness per tenant. Retries after timeout do not duplicate the operational event. A successful batch response returns `stored` as the number of accepted events so agents can safely clear their local queue after a committed transaction.

`PUT /devices/{device_id}/owner` move ou desvincula um dispositivo alterando `owner_membership_id`. A API valida tenant, hierarquia visível e registra auditoria.

Eventos ricos aceitos pelo agente:

- `app_focus_ended`
- `context_switch`
- `idle_started`
- `idle_ended`
- `session_locked`
- `session_unlocked`
- `user_logged_in`
- `user_logged_out`
- `machine_sleep`
- `machine_resume`
- `collection_quality`
- `agent_error`
- `agent_health`

`GET /operational-intelligence` retorna a visão profunda das últimas 24 horas, já filtrada por tenant e hierarquia:

- tempo ativo;
- tempo ocioso;
- taxa de ociosidade;
- trocas de contexto;
- trocas por hora;
- score de foco;
- dispersão operacional estimada;
- maior bloco contínuo de foco;
- tempo fragmentado;
- atividade atual;
- ranking por aplicativo/sistema;
- janelas somente quando a política permitir;
- linha do tempo ativa/ociosa;
- sinais de qualidade da coleta;
- resumo e recomendações determinísticas no formato de IA operacional.

## Insights Inteligentes

`GET /insights` retorna diagnosticos operacionais ja filtrados pelo tenant e pela hierarquia do usuario autenticado. Operadores recebem apenas seus proprios insights; gestores recebem a subarvore permitida; diretor/admin recebem a visao agregada do tenant.

Campos principais:

- `scopeType`, `scopeId`, `targetUserId`, `targetTeamId` e `targetDepartmentId`;
- `roleVisibility`;
- `insightType`;
- `title`, `summary`, `diagnosis` e `recommendation`;
- `evidence`, `metricsUsed`, `affectedUsers` e `affectedTeams`;
- `severity`, `confidence`, `estimatedTimeLoss`, `estimatedCostLoss` e `estimatedSavings`;
- `sentToWhatsapp`, `sentToEmail`, `whatsappStatus`, `emailStatus` e `lastSentAt`;
- `suggestedQuestions`, `status` e `actionStatus`.

`POST /insights/generate` gera e persiste um novo insight deterministico a partir de eventos reais no periodo informado (`24h`, `7d` ou `30d`). Quando GPT/Llama estiverem configurados, essa rota pode virar o ponto de orquestracao para enriquecimento por IA.

`POST /insights/{insight_id}/ask` aprofunda um insight dentro do mesmo escopo autorizado. Sem chave de IA real, responde com `aiMode=rules_fallback_explicit`, deixando claro que e fallback de regras.

`POST /insights/{insight_id}/send-whatsapp` e `POST /insights/{insight_id}/send-email` usam os servicos centrais de notificacao e salvam o status de entrega no metadata do insight.

`POST /insights/{insight_id}/create-action` cria um plano de acao vinculado ao insight no metadata atual. Antes do SaaS enterprise self-service, recomenda-se evoluir para uma tabela dedicada de acoes.

Mais detalhes: `docs/INSIGHTS.md`.

## Notificacoes

`GET /notifications` retorna historico, fila, tentativas, erro legivel, prioridade e status de entrega ja filtrados por tenant e hierarquia.

`GET /notifications/summary` retorna contadores para a central: pendentes, enviadas, falhas, criticas, nao lidas, canais e prioridades.

`GET /notification-types` retorna os 25 tipos operacionais padrao com prioridade, canais permitidos, audiencia e possibilidade de desativacao.

`GET /notification-templates` retorna os templates centrais. `POST /notification-templates/{template_id}/preview` renderiza variaveis sem disparar envio.

`POST /notifications/test` e `POST /notifications/send` usam `NotificationService` e gravam o resultado em `notifications`. Sem credenciais reais, o status fica explicito: `mocked`, `missing_credentials`, `missing_destination`, `failed` ou equivalente.

Quando `channel=whatsapp`, `POST /notifications/send` usa o Canal WhatsApp Raiz do Vulcan. O backend resolve destinatarios por tenant/hierarquia, grava `notifications`, cria itens em `whatsapp_delivery_queue`, processa envio imediato quando aplicavel e grava logs em `whatsapp_delivery_logs`.

`POST /notifications/{notification_id}/retry` tenta reenviar pelo provider configurado e incrementa tentativas. `cancel`, `mark-read` e `resolve` atualizam metadata com auditoria.

`GET /notifications/schedules` le agendamentos persistidos em `notifications` com `notification_type='schedule_config'`; se nao houver registros, devolve defaults comerciais. Endpoints `POST/PUT/DELETE/pause/resume` persistem a configuracao no mesmo modelo de compatibilidade.

## WhatsApp Raiz

`GET /integrations/whatsapp/status` retorna status do canal raiz: `connected`, `mock`, `missing_credentials` ou `disabled`.

`GET /integrations/whatsapp/evolution/status` retorna status detalhado da Evolution/Baileys: conectividade, instancia, QR, mock, credencial configurada, opt-in e fallbacks. Status nao oficial sempre usa prefixo `unofficial_*`.

`PUT /integrations/whatsapp/evolution/config` salva configuracao local/piloto quando permitido por `ALLOW_RUNTIME_INTEGRATION_CONFIG`. Secrets ficam mascarados e sao gravados no runtime store local, nao em Git.

`GET /integrations/whatsapp/evolution/qr` cria/consulta a instancia e retorna QR quando necessario. `POST /integrations/whatsapp/evolution/reconnect` reconfigura webhook e solicita reconexao.

`POST /integrations/whatsapp/evolution/webhook` e protegido por `X-Vulcan-Webhook-Token`, normaliza eventos da Evolution e atualiza `whatsapp_delivery_queue` quando ha `provider_message_id`.

`GET /integrations/whatsapp/root/recipients?notificationType=alerta&audience=managers` retorna destinatarios com WhatsApp cadastrado e preferencia habilitada, respeitando tenant e subarvore do usuario autenticado.

`POST /integrations/whatsapp/root/send` cria fila e, se `schedule=imediato`, tenta processar imediatamente.

Exemplo:

```json
{
  "tenantId": "00000000-0000-0000-0000-000000000301",
  "notificationType": "alerta",
  "title": "Gargalo detectado",
  "message": "A equipe financeira teve aumento de tempo no faturamento.",
  "audience": "managers",
  "priority": "alto",
  "schedule": "imediato"
}
```

`POST /integrations/whatsapp/root/process-queue` processa itens pendentes/due da fila. `GET /integrations/whatsapp/root/queue` e `GET /integrations/whatsapp/root/logs` exibem fila e historico. `POST /integrations/whatsapp/root/queue/{queue_id}/retry` reabre item falho sem criar duplicidade.

Mais detalhes: `docs/NOTIFICATIONS.md`, `docs/WHATSAPP.md`, `docs/WHATSAPP_EVOLUTION.md`, `docs/WHATSAPP_ROOT_CHANNEL.md`, `docs/EMAIL.md` e `docs/AGENT_NOTIFICATIONS.md`.

## Configuracoes

`GET /settings` retorna a central completa de configuracoes com summary, secoes, campos, escopo, status, editabilidade e mascaramento de secrets.

`PUT /settings/{section_id}` salva apenas campos conhecidos/editaveis da secao. Campos `secret` e `readonly` sao recusados pelo backend. Alteracoes persistem em `tenant_settings.settings` e geram `audit_logs`.

`POST /settings/{section_id}/test` valida a secao e retorna `ok`, `attention`, `missing`, `mock` ou `error` sem alterar dados.

Validacoes importantes:

- pesos de Metricas precisam somar 100%;
- screenshots e URL do navegador sao recusados por padrao;
- operador sem escopo de tenant nao altera configuracoes;
- secrets nunca voltam para o frontend.

Mais detalhes: `docs/SETTINGS.md` e `docs/CONFIGURATION.md`.

## Metricas Detalhadas E Exportacao

`GET /metrics/detailed` retorna ate 1000 eventos operacionais detalhados para a tela `Metricas`.

Parametros:

- `period`: `24h`, `7d`, `30d` ou `90d`;
- `teamId`;
- `membershipId`;
- `deviceId`;
- `supervisorId`;
- `department`;
- `title`;
- `os`;
- `category`;
- `agentStatus`;
- `metricType`;
- `app`.

Campos retornados:

- `id`;
- `tenantId`;
- `membershipId`;
- `userName`;
- `userTitle`;
- `supervisorId`;
- `supervisorName`;
- `teamId`;
- `teamName`;
- `department`;
- `deviceId`;
- `device`;
- `os`;
- `agentStatus`;
- `app`;
- `category`;
- `eventType`;
- `durationSeconds`;
- `occurredAt`;
- `collectionQuality`.

`GET /metrics/export` usa os mesmos filtros e aceita `format=csv` ou `format=excel`. A resposta e um arquivo CSV com BOM UTF-8, metadados de filtro e tabela detalhada.

`metricType` aceita:

- `productive`;
- `idle`;
- `context_switch`;
- `agent`;
- `improductive`;
- ou um `event_type` especifico.

Todos os filtros passam pelo contexto autenticado, tenant e hierarquia visivel. Supervisor e usuario sao validados contra o escopo permitido antes da consulta.

## Ingestion Gateway

Base service: `backend/ingestion-gateway`

- `GET /health`
- `POST /v1/operational-events/batches`

Headers:

- `X-Ingestion-Key-Id`
- `X-Ingestion-Key`

## Query API

Base service: `backend/query-api`

- `GET /health`
- `GET /v1/daily-user-operational-metrics`
- `GET /v1/session-slices`
- `GET /v1/idle-windows`
- `GET /v1/application-usage-facts`

Local development can use fixtures; production must validate Supabase Auth and enforce tenant RLS.

## AI API

Base service: `ai/api`

- `GET /health`
- `POST /v1/insights/explain`

The AI API must be called with tenant-scoped structured facts only.
