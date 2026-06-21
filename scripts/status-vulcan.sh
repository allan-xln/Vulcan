#!/usr/bin/env bash

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT_DIR/.runtime/pids"
API_URL="http://127.0.0.1:${LOCAL_API_PORT:-3001}"
FRONTEND_PORT="$(cat "$ROOT_DIR/.runtime/frontend-port" 2>/dev/null || echo "${FRONTEND_PORT:-3002}")"

for name in backend frontend whatsapp-worker; do
  pid_file="$PID_DIR/$name.pid"
  if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$name: rodando (PID $(cat "$pid_file"))"
  else
    echo "$name: parado ou não gerenciado"
  fi
done

printf 'backend health: '
curl -fsS "$API_URL/health" >/dev/null && echo "OK" || echo "FALHOU"
printf 'frontend health: '
curl -fsS "http://127.0.0.1:$FRONTEND_PORT/" >/dev/null && echo "OK ($FRONTEND_PORT)" || echo "FALHOU ($FRONTEND_PORT)"

if [ -f "$ROOT_DIR/.runtime/whatsapp-worker-health.json" ]; then
  echo "worker/fila:"
  cat "$ROOT_DIR/.runtime/whatsapp-worker-health.json"
fi

token="$(curl -fsS -X POST "$API_URL/auth/login" -H 'Content-Type: application/json' -d '{"username":"teste","password":"teste"}' 2>/dev/null | jq -r '.accessToken // empty' || true)"
if [ -n "$token" ]; then
  echo "WhatsApp provider:"
  curl -fsS "$API_URL/integrations/whatsapp/status" -H "Authorization: Bearer $token" | jq '{provider,status,connected,qrRequired,rootChannelNumber}' || true
  echo "Supabase:"
  curl -fsS "$API_URL/supabase/status" -H "Authorization: Bearer $token" | jq '{configured,databaseReachable,restReachable}' || true
fi
