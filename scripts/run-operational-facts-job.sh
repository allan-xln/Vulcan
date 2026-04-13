#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "Python virtualenv is missing. Run ./scripts/bootstrap.sh first." >&2
  exit 1
fi

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

export PYTHONPATH="$ROOT_DIR/services/jobs${PYTHONPATH:+:$PYTHONPATH}"

"$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/services/jobs/app/run_operational_facts.py" "$@"
