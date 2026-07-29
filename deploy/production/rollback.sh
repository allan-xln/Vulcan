#!/usr/bin/env bash

set -euo pipefail

if [[ -z "${1:-}" || ! -d "${1:-}" ]]; then
  echo "Uso: $0 /diretorio/da/release-anterior" >&2
  exit 1
fi

PREVIOUS_RELEASE="$(cd "$1" && pwd)"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -x "$PREVIOUS_RELEASE/deploy.sh" || ! -f "$PREVIOUS_RELEASE/.env.production" ]]; then
  echo "A release anterior não contém deploy.sh e .env.production válidos." >&2
  exit 1
fi

if [[ -f "$PREVIOUS_RELEASE/images/vulcan-images.tar.gz" ]]; then
  gzip -dc "$PREVIOUS_RELEASE/images/vulcan-images.tar.gz" | docker load >/dev/null
fi

docker compose --env-file "$CURRENT_DIR/.env.production" -f "$CURRENT_DIR/compose.yml" \
  --profile core stop backend whatsapp-worker frontend edge
docker compose --env-file "$PREVIOUS_RELEASE/.env.production" -f "$PREVIOUS_RELEASE/compose.yml" \
  --profile core up -d --wait
"$PREVIOUS_RELEASE/healthcheck.sh"

echo "Rollback de imagens concluído. Nenhuma reversão destrutiva de banco foi executada."
