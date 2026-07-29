#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DEPLOY_DIR/.env.production"

docker compose --env-file "$ENV_FILE" -f "$DEPLOY_DIR/compose.yml" \
  --profile core logs --tail "${VULCAN_LOG_LINES:-200}" "$@"
