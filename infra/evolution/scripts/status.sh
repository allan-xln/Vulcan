#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_docker
[ -f "$ENV_FILE" ] || { echo "Evolution: não configurada (.env ausente)."; exit 1; }
compose ps
set -a
source "$ENV_FILE"
set +a
printf '\nHealth HTTP: '
curl -fsS "http://127.0.0.1:${EVOLUTION_PORT:-8080}/" >/dev/null && echo "OK" || echo "FALHOU"
printf 'Instância vulcan-root: '
curl -fsS -H "apikey: $EVOLUTION_API_KEY" "http://127.0.0.1:${EVOLUTION_PORT:-8080}/instance/connectionState/vulcan-root" 2>/dev/null || echo "ainda não criada/QR pendente"
echo
