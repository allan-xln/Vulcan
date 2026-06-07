#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

if command -v pnpm >/dev/null 2>&1; then
  PNPM_CMD=(pnpm)
elif command -v corepack >/dev/null 2>&1; then
  PNPM_CMD=(corepack pnpm)
else
  echo "pnpm or corepack is required" >&2
  exit 1
fi

"${PNPM_CMD[@]}" --dir frontend/web lint
"${PNPM_CMD[@]}" --dir frontend/web typecheck
"${PNPM_CMD[@]}" --dir frontend/web test:unit
"${PNPM_CMD[@]}" --dir frontend/web build
"$ROOT_DIR/.venv/bin/python" -m pytest ai/api/tests
"$ROOT_DIR/.venv/bin/python" -m pytest backend/api/tests
