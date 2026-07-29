#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DEPLOY_DIR/.env.production"
RESTORE_DIR=""

if [[ "${1:-}" == "--restore-dir" ]]; then
  RESTORE_DIR="${2:-}"
  if [[ -z "$RESTORE_DIR" || ! -d "$RESTORE_DIR" ]]; then
    echo "--restore-dir exige um diretório de backup válido" >&2
    exit 1
  fi
elif [[ $# -gt 0 ]]; then
  echo "Uso: $0 [--restore-dir /caminho/do/backup]" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$DEPLOY_DIR/.env.production.example" "$ENV_FILE"
  chmod 0600 "$ENV_FILE"
  echo "Revise $ENV_FILE e execute novamente." >&2
  exit 1
fi

"$DEPLOY_DIR/init-secrets.sh"

if [[ -f "$DEPLOY_DIR/images/vulcan-images.tar.gz" ]]; then
  gzip -dc "$DEPLOY_DIR/images/vulcan-images.tar.gz" | docker load >/dev/null
fi

compose=(docker compose --env-file "$ENV_FILE" -f "$DEPLOY_DIR/compose.yml")
"${compose[@]}" --profile core config --quiet
"${compose[@]}" --profile core up -d --wait db evolution-db evolution-redis
"${compose[@]}" --profile core run --rm runtime-init

if [[ -n "$RESTORE_DIR" ]]; then
  "$DEPLOY_DIR/restore.sh" --initial "$RESTORE_DIR"
fi

"${compose[@]}" --profile core up -d --wait

if grep -Eq '^DISCOVERY_ENABLED=(true|1|yes)$' "$ENV_FILE"; then
  "${compose[@]}" --profile core --profile network up -d --wait discovery
fi

"$DEPLOY_DIR/healthcheck.sh"
