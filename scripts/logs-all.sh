#!/usr/bin/env bash

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "${1:-}" = "--follow" ] || [ "${1:-}" = "-f" ]; then
  echo "Use dois terminais para follow simultâneo: scripts/logs-vulcan.sh -f e infra/evolution/scripts/logs.sh -f"
  "$ROOT_DIR/scripts/logs-vulcan.sh" -f
  exit 0
fi

echo "===== Evolution ====="
"$ROOT_DIR/infra/evolution/scripts/logs.sh" || true
echo "===== Vulcan ====="
"$ROOT_DIR/scripts/logs-vulcan.sh" || true
