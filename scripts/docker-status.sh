#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker-common.sh"

ensure_docker_env
require_docker

compose ps

BACKEND_PORT="$(sed -n 's/^BACKEND_PORT=//p' "$DOCKER_ENV_FILE" | head -n1)"
FRONTEND_PORT="$(sed -n 's/^FRONTEND_PORT=//p' "$DOCKER_ENV_FILE" | head -n1)"
OWNER_USERNAME="$(sed -n 's/^LOCAL_ADMIN_USERNAME=//p' "$DOCKER_ENV_FILE" | head -n1)"
OWNER_PASSWORD="$(sed -n 's/^LOCAL_ADMIN_PASSWORD=//p' "$DOCKER_ENV_FILE" | head -n1)"
BACKEND_PORT="${BACKEND_PORT:-3001}"
FRONTEND_PORT="${FRONTEND_PORT:-3002}"
OWNER_USERNAME="${OWNER_USERNAME:-admin}"
OWNER_PASSWORD="${OWNER_PASSWORD:-admin}"

wait_http() {
  local label="$1"
  local url="$2"
  shift 2
  printf '%s: ' "$label"
  for _ in $(seq 1 30); do
    if curl -fsS "$@" "$url" >/dev/null 2>&1; then
      echo "OK"
      return 0
    fi
    sleep 2
  done
  echo "FALHOU"
  return 1
}

echo
wait_http "Backend health" "http://127.0.0.1:$BACKEND_PORT/health" || true
wait_http "Frontend health" "http://127.0.0.1:$FRONTEND_PORT/" || true
printf 'Evolution container: '
evolution_health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' vulcan-evolution-api 2>/dev/null || true)"
if [ "$evolution_health" = "healthy" ] || [ "$evolution_health" = "running" ]; then
  echo "OK ($evolution_health, interno no Docker)"
else
  echo "FALHOU (${evolution_health:-ausente})"
fi

if command -v jq >/dev/null 2>&1; then
  token="$(curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/auth/login" -H 'Content-Type: application/json' -d "{\"username\":\"$OWNER_USERNAME\",\"password\":\"$OWNER_PASSWORD\"}" 2>/dev/null | jq -r '.accessToken // empty' || true)"
  if [ -n "$token" ]; then
    echo "WhatsApp provider:"
    curl -fsS "http://127.0.0.1:$BACKEND_PORT/integrations/whatsapp/evolution/status" -H "Authorization: Bearer $token" | jq '{provider,status,connected,qrRequired,apiKeyConfigured,rootNumber}'
  fi
fi
