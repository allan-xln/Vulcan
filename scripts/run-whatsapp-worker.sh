#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

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
exec "$ROOT_DIR/.venv/bin/python" -m app.whatsapp_worker "$@"
