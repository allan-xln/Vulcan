#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/docker/.env"
EXAMPLE_FILE="$ROOT_DIR/docker/.env.example"

if [ -f "$ENV_FILE" ]; then
  echo "$ENV_FILE já existe."
  exit 0
fi

command -v openssl >/dev/null 2>&1 || {
  echo "openssl é necessário para gerar secrets locais." >&2
  exit 1
}

umask 077
cp "$EXAMPLE_FILE" "$ENV_FILE"
sed -i "s|^EVOLUTION_API_KEY=.*|EVOLUTION_API_KEY=$(openssl rand -hex 32)|" "$ENV_FILE"
sed -i "s|^EVOLUTION_WEBHOOK_TOKEN=.*|EVOLUTION_WEBHOOK_TOKEN=$(openssl rand -hex 32)|" "$ENV_FILE"
sed -i "s|^EVOLUTION_POSTGRES_PASSWORD=.*|EVOLUTION_POSTGRES_PASSWORD=$(openssl rand -hex 24)|" "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "Criado $ENV_FILE com secrets locais protegidos."
