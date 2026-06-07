#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "Python virtualenv is missing. Run ./scripts/bootstrap.sh first." >&2
  exit 1
fi

"$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/scripts/seed_demo.py"
