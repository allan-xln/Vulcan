# Backend

## Services

- `backend/api`: API SaaS local para autenticação, dashboard, hierarquia, IA, Supabase, notificações, WhatsApp, e-mail e agentes.
- `backend/ingestion-gateway`: fronteira de ingestão de eventos operacionais.
- `backend/query-api`: API de leitura por tenant para métricas e fatos derivados.
- `backend/jobs`: processamento determinístico em segundo plano.

## Local SaaS API

Run:

```bash
./scripts/run-api.sh
```

Default URL:

```text
http://localhost:3001
```

## Temporary Local Authentication

Credentials:

```text
username: admin
password: admin
```

This is development-only and must be replaced before production.

Também existe o usuário local de teste:

```text
username: teste
password: teste
```

Ele deve ser usado apenas em desenvolvimento para validar métricas reais do notebook.

## Implemented Local Endpoints

- `GET /health`
- `POST /auth/login`
- `GET /tenants`
- `GET /users`
- `GET /hierarchy`
- `GET /devices`
- `GET /activity-events`
- `GET /metrics`
- `GET /insights`
- `GET /notifications`
- `POST /notifications/send`
- `GET /notifications/preferences`
- `GET /notifications/schedules`
- `GET /reports/templates`
- `GET /integrations/whatsapp/status`
- `POST /integrations/whatsapp/test`
- `GET /integrations/email/status`
- `POST /integrations/email/test`
- `GET /integrations/status`
- `POST /ai/analyze`
- `POST /ai/copilot`
- `GET /supabase/status`
- `GET /agent/status`
- `POST /agent/enroll`
- `POST /agent/heartbeat`
- `POST /agent/events`
- `POST /agent/sync`
- `POST /agent/logs`

Protected endpoints require:

```text
Authorization: Bearer dev-vulcan-admin-token
```

## Integrações

WhatsApp fica em `backend/api/app/whatsapp.py`. A implementação é própria do Vulcan e foi apenas inspirada no padrão arquitetural do LanChat: sessão, status, QR quando necessário, logs e teste de envio. O LanChat não é alterado nem importado.

E-mail fica em `backend/api/app/email_channels.py` com SMTP, Gmail, Outlook, IMAP e POP3. SMTP/OAuth são prioridade para envio. IMAP e POP3 são canais de leitura/consulta.

## Direção De Produção

Produção deve validar Supabase Auth, aplicar filtros por tenant em toda consulta, manter RLS ativo, armazenar segredos em cofre seguro por tenant e registrar auditoria em ações sensíveis.

## Agent Gateway

The agent gateway is part of `backend/api`. It accepts enrollment, heartbeat, event sync and logs from local agents. Requests are not tied to a dashboard user session; they are authenticated with `AGENT_ENROLLMENT_TOKEN` and persisted under the request `tenant_id`.

Current persistence:

- enrollment upserts `devices`;
- heartbeat updates `devices.last_seen_at`, `status`, fila offline, IP local, versao, erro, saude e qualidade de coleta;
- event sync inserts rich `activity_events` and derived `operational_metrics`;
- each critical action writes `audit_logs`.
- `PUT /devices/{device_id}/owner` move or unlinks a device from a visible hierarchy membership and writes audit.

Rich event types accepted by the gateway:

- `app_focus_started`
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
- `heartbeat`
- `sync_status`
- `collection_quality`
- `agent_error`
- `agent_health`

Production should evolve this into tenant-scoped enrollment tokens with expiration, revocation and per-device signing keys.
