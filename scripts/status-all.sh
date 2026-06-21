#!/usr/bin/env bash

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "===== Evolution ====="
"$ROOT_DIR/infra/evolution/scripts/status.sh" || true
echo "===== Vulcan ====="
"$ROOT_DIR/scripts/status-vulcan.sh" || true
