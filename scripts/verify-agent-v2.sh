#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_DATABASE_URL="${VULCAN_AGENT_DATABASE_URL:-postgresql://postgres:postgres@127.0.0.1:55432/vulcan}"
GO_BINARY="${GO_BINARY:-$ROOT_DIR/.tools/go/bin/go}"

if [ ! -x "$GO_BINARY" ]; then
  GO_BINARY="$(command -v go || true)"
fi
if [ -z "$GO_BINARY" ] || [ ! -x "$GO_BINARY" ]; then
  echo "Go toolchain is required for Vulcan Agent verification" >&2
  exit 1
fi

VALIDATION_SQL="$ROOT_DIR/database/supabase/validation/008_agent_v2_checks.sql"

if psql "$AGENT_DATABASE_URL" -Atqc "select 1" >/dev/null 2>&1; then
  psql "$AGENT_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$VALIDATION_SQL"
elif command -v docker >/dev/null 2>&1 \
  && [ "$(docker inspect -f '{{.State.Running}}' vulcan-db 2>/dev/null || true)" = "true" ]; then
  docker exec -i vulcan-db sh -lc \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1' \
    < "$VALIDATION_SQL"
else
  echo "PostgreSQL is unavailable through $AGENT_DATABASE_URL and vulcan-db is not running" >&2
  exit 1
fi

(
  cd "$ROOT_DIR/agentes/agent"
  "$GO_BINARY" test -race ./...
  "$GO_BINARY" vet ./...
  GOOS=windows GOARCH=amd64 "$GO_BINARY" test -exec=/bin/true ./...
  GOOS=windows GOARCH=amd64 "$GO_BINARY" vet ./...
)

AUTH_PROVIDER=supabase \
MOCK_AUTH=true \
MOCK_DATA=true \
PYTHONPATH="$ROOT_DIR/backend/api" \
  "$ROOT_DIR/.venv/bin/python" -m pytest "$ROOT_DIR/backend/api/tests/test_agent_v2.py" -q

echo "Vulcan Agent v2 verification passed"
