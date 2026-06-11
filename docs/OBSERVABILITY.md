# Observability

## Current Signals

- `GET /health` for API liveness.
- `GET /supabase/status` for Supabase configuration, REST reachability and direct database reachability.
- integration status endpoints for WhatsApp and e-mail.
- AI status endpoint.
- agent queue depth, last sync and collection quality.
- notification logs and audit records.

## Local Checks

```bash
curl http://localhost:3001/health
curl http://localhost:3001/supabase/status
```

Authenticated checks:

```bash
TOKEN=$(curl -sS -H "Content-Type: application/json" \
  -d '{"username":"teste","password":"teste"}' \
  http://localhost:3001/auth/login | python3 -c 'import sys,json; print(json.load(sys.stdin)["accessToken"])')

curl -H "Authorization: Bearer $TOKEN" http://localhost:3001/ai/status
curl -H "Authorization: Bearer $TOKEN" http://localhost:3001/integrations/whatsapp/status
curl -H "Authorization: Bearer $TOKEN" http://localhost:3001/integrations/email/status
```

## Production Plan

- structured JSON logs for API, jobs and agents;
- request id propagation;
- tenant id and user id in audit-safe logs;
- secrets masked in all logs;
- Sentry or equivalent for frontend/backend exceptions;
- OpenTelemetry traces for API, database and provider calls;
- uptime monitor for `/health`;
- alert when database is unreachable;
- alert when agent queue grows above threshold;
- alert when notification delivery fails repeatedly;
- daily backup check and restore drill.

## Important Failure Mode

Supabase REST may be reachable while direct PostgreSQL is blocked by network, IPv6 or firewall. `/supabase/status` exposes both `restReachable` and `databaseReachable` so the frontend can avoid noisy failing requests and show a controlled degraded state.
