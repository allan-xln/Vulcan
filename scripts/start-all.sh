#!/usr/bin/env bash

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT_DIR/infra/evolution/scripts/start.sh"
"$ROOT_DIR/scripts/start-vulcan.sh"
"$ROOT_DIR/scripts/status-all.sh"
