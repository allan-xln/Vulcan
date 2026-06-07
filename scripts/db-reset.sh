#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

docker compose -f "$ROOT_DIR/docker/compose.yml" stop db || true
docker compose -f "$ROOT_DIR/docker/compose.yml" rm -fsv db || true
docker volume rm vulcan_postgres-data >/dev/null 2>&1 || true
docker compose -f "$ROOT_DIR/docker/compose.yml" up -d db
