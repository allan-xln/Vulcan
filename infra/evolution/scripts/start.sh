#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

ensure_env
require_docker
compose up -d --wait
echo "Evolution API: http://127.0.0.1:$(sed -n 's/^EVOLUTION_PORT=//p' "$ENV_FILE")"
echo "Próximo passo: abra Configurações > WhatsApp no Vulcan e gere o QR Code."
