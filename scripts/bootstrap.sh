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

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is required for database validation" >&2
  exit 1
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
else
  echo ".env already exists"
fi

"${PNPM_CMD[@]}" install

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  echo "Created Python virtual environment in .venv"
fi

"$ROOT_DIR/.venv/bin/python" -m pip install --upgrade pip >/dev/null
"$ROOT_DIR/.venv/bin/pip" install --no-build-isolation "$ROOT_DIR/ai/api[dev]" >/dev/null
"$ROOT_DIR/.venv/bin/pip" install --no-build-isolation "$ROOT_DIR/backend/api[dev]" >/dev/null
"$ROOT_DIR/.venv/bin/pip" install --no-build-isolation "$ROOT_DIR/backend/ingestion-gateway[dev]" >/dev/null
"$ROOT_DIR/.venv/bin/pip" install --no-build-isolation "$ROOT_DIR/backend/jobs[dev]" >/dev/null
"$ROOT_DIR/.venv/bin/pip" install --no-build-isolation "$ROOT_DIR/backend/query-api[dev]" >/dev/null

echo "Bootstrap complete"
