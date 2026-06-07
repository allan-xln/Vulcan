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
- `GET /operational-metrics`
- `GET /operational-intelligence`
- `GET /insights`
- `GET /notifications`
- `POST /notifications/test`
- `POST /notifications/send`
- `GET /notifications/preferences`
- `PUT /notifications/preferences/{preference_id}`
- `GET /notifications/schedules`
- `GET /reports/templates`
- `GET /integrations/whatsapp/status`
- `POST /integrations/whatsapp/test`
- `GET /integrations/email/status`
- `POST /integrations/email/test`
- `GET /integrations/status`
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

Membership manager changes reject cycles and refresh `membership_closure`. Activity event ingestion persists the event, writes an `operational_metrics` row, and records an audit log.

Agent endpoints are intentionally separated from dashboard auth. They require `enrollmentToken` matching `AGENT_ENROLLMENT_TOKEN`, write tenant-scoped device/activity/metric records, and keep local agent operation independent from a human dashboard session.

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
