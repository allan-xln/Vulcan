#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_docker
ensure_env
compose restart evolution
compose up -d --wait
"$EVOLUTION_DIR/scripts/status.sh"
