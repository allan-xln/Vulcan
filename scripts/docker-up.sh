#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker-common.sh"

ensure_docker_env
require_docker

"$ROOT_DIR/scripts/stop-vulcan.sh" >/dev/null 2>&1 || true

echo "Subindo banco e Evolution..."
compose up -d --build db evolution-db evolution-redis evolution

echo "Aplicando migrations e seed demo dentro do Docker..."
compose run --rm migrate

echo "Subindo backend, worker e frontend..."
compose up -d --build backend whatsapp-worker frontend

"$ROOT_DIR/scripts/docker-status.sh"

env_value() {
  local key="$1"
  local fallback="$2"
  local value
  value="$(sed -n "s/^${key}=//p" "$DOCKER_ENV_FILE" | head -n1)"
  printf "%s" "${value:-$fallback}"
}

echo
echo "Frontend:  http://localhost:$(env_value FRONTEND_PORT 3002)"
echo "Backend:   http://localhost:$(env_value BACKEND_PORT 3001)"
echo "Evolution: http://localhost:$(env_value EVOLUTION_PORT 8080)"
echo
echo "Para conectar o celular no WhatsApp mestre:"
echo "  ./scripts/docker-whatsapp-qr.sh 55DDDNUMERO"
