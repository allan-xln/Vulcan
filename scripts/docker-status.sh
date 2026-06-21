#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker-common.sh"

ensure_docker_env
require_docker

compose ps

BACKEND_PORT="$(sed -n 's/^BACKEND_PORT=//p' "$DOCKER_ENV_FILE" | head -n1)"
FRONTEND_PORT="$(sed -n 's/^FRONTEND_PORT=//p' "$DOCKER_ENV_FILE" | head -n1)"
EVOLUTION_PORT="$(sed -n 's/^EVOLUTION_PORT=//p' "$DOCKER_ENV_FILE" | head -n1)"
BACKEND_PORT="${BACKEND_PORT:-3001}"
FRONTEND_PORT="${FRONTEND_PORT:-3002}"
EVOLUTION_PORT="${EVOLUTION_PORT:-8080}"

printf '\nBackend health: '
curl -fsS "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null && echo "OK" || echo "FALHOU"

printf 'Frontend health: '
curl -fsS "http://127.0.0.1:$FRONTEND_PORT/" >/dev/null && echo "OK" || echo "FALHOU"

printf 'Evolution health: '
curl -fsS "http://127.0.0.1:$EVOLUTION_PORT/" >/dev/null && echo "OK" || echo "FALHOU"

if command -v jq >/dev/null 2>&1; then
  token="$(curl -fsS -X POST "http://127.0.0.1:$BACKEND_PORT/auth/login" -H 'Content-Type: application/json' -d '{"username":"teste","password":"teste"}' 2>/dev/null | jq -r '.accessToken // empty' || true)"
  if [ -n "$token" ]; then
    echo "WhatsApp provider:"
    curl -fsS "http://127.0.0.1:$BACKEND_PORT/integrations/whatsapp/evolution/status" -H "Authorization: Bearer $token" | jq '{provider,status,connected,qrRequired,apiKeyConfigured,rootNumber}'
  fi
fi
