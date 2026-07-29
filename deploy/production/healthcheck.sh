#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DEPLOY_DIR/.env.production"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Arquivo ausente: $ENV_FILE" >&2
  exit 1
fi

public_url="$(sed -n 's/^VULCAN_PUBLIC_URL=//p' "$ENV_FILE" | tail -n 1)"
if [[ -z "$public_url" ]]; then
  echo "VULCAN_PUBLIC_URL não está configurada" >&2
  exit 1
fi

for endpoint in healthz readyz livez version; do
  curl --fail --silent --show-error --max-time 10 "$public_url/$endpoint" >/dev/null
  echo "OK $public_url/$endpoint"
done

curl --fail --silent --show-error --max-time 10 "$public_url/" >/dev/null
curl --fail --silent --show-error --max-time 10 "$public_url/wallboard" >/dev/null
echo "OK $public_url/"
echo "OK $public_url/wallboard"

docker compose --env-file "$ENV_FILE" -f "$DEPLOY_DIR/compose.yml" --profile core ps
