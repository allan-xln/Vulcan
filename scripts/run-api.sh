#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -x "$ROOT_DIR/.venv/bin/uvicorn" ]; then
  echo "Python virtualenv is missing. Run ./scripts/bootstrap.sh first." >&2
  exit 1
fi

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

if [ -f "$ROOT_DIR/infra/evolution/.env" ]; then
  set -a
  source "$ROOT_DIR/infra/evolution/.env"
  set +a
fi

export PYTHONPATH="$ROOT_DIR/backend/api${PYTHONPATH:+:$PYTHONPATH}"

UVICORN_ARGS=(
  app.main:app
  --host "${LOCAL_API_HOST:-0.0.0.0}"
  --port "${LOCAL_API_PORT:-3001}"
  --app-dir "$ROOT_DIR/backend/api"
)

if [ "${VULCAN_API_RELOAD:-true}" = "true" ]; then
  UVICORN_ARGS+=(--reload --reload-dir "$ROOT_DIR/backend/api")
fi

exec "$ROOT_DIR/.venv/bin/uvicorn" "${UVICORN_ARGS[@]}"
