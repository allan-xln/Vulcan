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

export PYTHONPATH="$ROOT_DIR/backend/api${PYTHONPATH:+:$PYTHONPATH}"

"$ROOT_DIR/.venv/bin/uvicorn" app.main:app \
  --reload \
  --host "${LOCAL_API_HOST:-0.0.0.0}" \
  --port "${LOCAL_API_PORT:-3001}" \
  --app-dir "$ROOT_DIR/backend/api"
