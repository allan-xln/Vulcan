#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test:unit
pnpm --dir apps/web build
"$ROOT_DIR/.venv/bin/python" -m pytest services/ai-api/tests
