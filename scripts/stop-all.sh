#!/usr/bin/env bash

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"$ROOT_DIR/scripts/stop-vulcan.sh"
"$ROOT_DIR/infra/evolution/scripts/stop.sh"
