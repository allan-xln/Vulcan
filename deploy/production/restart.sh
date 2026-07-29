#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DEPLOY_DIR/.env.production"
compose=(docker compose --env-file "$ENV_FILE" -f "$DEPLOY_DIR/compose.yml")

"${compose[@]}" --profile core restart backend whatsapp-worker frontend edge
"${compose[@]}" --profile core up -d --wait
"$DEPLOY_DIR/healthcheck.sh"
