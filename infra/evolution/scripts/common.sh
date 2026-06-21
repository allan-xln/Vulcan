#!/usr/bin/env bash

set -euo pipefail

EVOLUTION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$EVOLUTION_DIR/.env"
COMPOSE_FILE="$EVOLUTION_DIR/docker-compose.yml"

require_docker() {
  command -v docker >/dev/null 2>&1 || { echo "Docker não está instalado." >&2; exit 1; }
  docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 não está disponível." >&2; exit 1; }
  docker info >/dev/null 2>&1 || {
    echo "Sem acesso ao Docker daemon. Execute como usuário do grupo docker ou ajuste a instalação rootless." >&2
    exit 1
  }
}

ensure_env() {
  if [ -f "$ENV_FILE" ]; then
    return
  fi
  command -v openssl >/dev/null 2>&1 || { echo "openssl é necessário para gerar secrets locais." >&2; exit 1; }
  umask 077
  cp "$EVOLUTION_DIR/.env.example" "$ENV_FILE"
  sed -i "s|^EVOLUTION_API_KEY=.*|EVOLUTION_API_KEY=$(openssl rand -hex 32)|" "$ENV_FILE"
  sed -i "s|^EVOLUTION_WEBHOOK_TOKEN=.*|EVOLUTION_WEBHOOK_TOKEN=$(openssl rand -hex 32)|" "$ENV_FILE"
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Criado $ENV_FILE com secrets locais protegidos."
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}
