#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_docker
[ -f "$ENV_FILE" ] || { echo "Evolution ainda não foi configurada."; exit 1; }
if [ "${1:-}" = "--follow" ] || [ "${1:-}" = "-f" ]; then
  compose logs --tail=200 -f evolution postgres redis
else
  compose logs --tail=200 evolution postgres redis
fi
