#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_docker
[ -f "$ENV_FILE" ] || { echo "Evolution ainda não foi configurada."; exit 0; }
compose down
