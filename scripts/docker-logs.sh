#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker-common.sh"

ensure_docker_env
require_docker

if [ "${1:-}" = "--follow" ] || [ "${1:-}" = "-f" ]; then
  shift
  compose logs -f "$@"
else
  compose logs --tail=150 "$@"
fi
