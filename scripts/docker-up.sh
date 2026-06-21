#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker-common.sh"

ensure_docker_env
require_docker

"$ROOT_DIR/scripts/stop-vulcan.sh" >/dev/null 2>&1 || true

env_value() {
  local key="$1"
  local fallback="$2"
  local value
  value="$(sed -n "s/^${key}=//p" "$DOCKER_ENV_FILE" | head -n1)"
  printf "%s" "${value:-$fallback}"
}

set_env_value() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "$DOCKER_ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$DOCKER_ENV_FILE"
  else
    printf "\n%s=%s\n" "$key" "$value" >> "$DOCKER_ENV_FILE"
  fi
}

container_running() {
  docker ps --format '{{.Names}}' | grep -qx "$1"
}

port_listening() {
  local port="$1"
  command -v ss >/dev/null 2>&1 || return 1
  ss -ltnH | awk '{print $4}' | grep -Eq "(^|:)${port}$"
}

next_free_port() {
  local port="$1"
  while port_listening "$port"; do
    port=$((port + 1))
  done
  printf "%s" "$port"
}

avoid_port_conflict() {
  local key="$1"
  local fallback="$2"
  local container="$3"
  if container_running "$container"; then
    return
  fi
  local current
  current="$(env_value "$key" "$fallback")"
  if port_listening "$current"; then
    local next
    next="$(next_free_port "$((current + 1))")"
    set_env_value "$key" "$next"
    echo "Porta $current ocupada; usando ${key}=$next."
  fi
}

avoid_port_conflict VULCAN_DB_PORT 55432 vulcan-db
avoid_port_conflict EVOLUTION_PORT 8080 vulcan-evolution-api
avoid_port_conflict BACKEND_PORT 3001 vulcan-backend
avoid_port_conflict FRONTEND_PORT 3002 vulcan-frontend

EVOLUTION_PORT_VALUE="$(env_value EVOLUTION_PORT 8080)"
set_env_value EVOLUTION_REQUEST_ORIGIN "http://localhost:${EVOLUTION_PORT_VALUE}"
set_env_value EVOLUTION_CORS_ORIGIN "http://localhost:${EVOLUTION_PORT_VALUE},http://127.0.0.1:${EVOLUTION_PORT_VALUE}"

echo "Subindo banco e Evolution..."
compose up -d --build db evolution-db evolution-redis evolution

echo "Construindo imagem do backend/migrations..."
compose build backend migrate

echo "Aplicando migrations e seed demo dentro do Docker..."
compose run --rm migrate

echo "Subindo backend, worker e frontend..."
compose up -d --build backend whatsapp-worker frontend

"$ROOT_DIR/scripts/docker-status.sh"

echo
echo "Frontend:  http://localhost:$(env_value FRONTEND_PORT 3002)"
echo "Backend:   http://localhost:$(env_value BACKEND_PORT 3001)"
echo "Evolution: http://localhost:$(env_value EVOLUTION_PORT 8080)"
echo
echo "Para conectar o celular no WhatsApp mestre:"
echo "  ./scripts/docker-whatsapp-qr.sh 55DDDNUMERO"
