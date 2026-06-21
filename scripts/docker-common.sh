#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_ENV_FILE="$ROOT_DIR/docker/.env"
DOCKER_COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"

ensure_docker_env() {
  "$ROOT_DIR/scripts/docker-init-env.sh"
}

require_docker() {
  command -v docker >/dev/null 2>&1 || {
    echo "Docker não está instalado." >&2
    exit 1
  }
  docker compose version >/dev/null 2>&1 || {
    echo "Docker Compose v2 não está disponível." >&2
    exit 1
  }
  docker info >/dev/null 2>&1 || {
    echo "Sem acesso ao Docker daemon. Rode como usuário do grupo docker, use sudo, ou ajuste Docker rootless." >&2
    exit 1
  }
}

compose() {
  docker compose --env-file "$DOCKER_ENV_FILE" -f "$DOCKER_COMPOSE_FILE" "$@"
}
