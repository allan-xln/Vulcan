#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/docker-common.sh"

ensure_docker_env
require_docker

command -v jq >/dev/null 2>&1 || {
  echo "jq é necessário para ler a resposta do backend." >&2
  exit 1
}

MASTER_NUMBER="${1:-}"
BACKEND_PORT="$(sed -n 's/^BACKEND_PORT=//p' "$DOCKER_ENV_FILE" | head -n1)"
OWNER_USERNAME="$(sed -n 's/^LOCAL_ADMIN_USERNAME=//p' "$DOCKER_ENV_FILE" | head -n1)"
OWNER_PASSWORD="$(sed -n 's/^LOCAL_ADMIN_PASSWORD=//p' "$DOCKER_ENV_FILE" | head -n1)"
BACKEND_PORT="${BACKEND_PORT:-3001}"
OWNER_USERNAME="${OWNER_USERNAME:-admin}"
OWNER_PASSWORD="${OWNER_PASSWORD:-admin}"
API_URL="http://127.0.0.1:$BACKEND_PORT"
TENANT_ID="00000000-0000-0000-0000-000000000301"

if [ -n "$MASTER_NUMBER" ]; then
  digits="$(printf "%s" "$MASTER_NUMBER" | tr -cd '0-9')"
  if [ "${#digits}" -lt 10 ] || [ "${#digits}" -gt 15 ] || [ "${digits#0}" != "$digits" ]; then
    echo "Número inválido. Use E.164 só com dígitos, exemplo: 5541999999999." >&2
    exit 1
  fi
  MASTER_NUMBER="$digits"
fi

token="$(curl -fsS -X POST "$API_URL/auth/login" -H 'Content-Type: application/json' -d "{\"username\":\"$OWNER_USERNAME\",\"password\":\"$OWNER_PASSWORD\"}" | jq -r '.accessToken')"

if [ -n "$MASTER_NUMBER" ]; then
  curl -fsS -X PUT "$API_URL/integrations/whatsapp/evolution/config" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: $TENANT_ID" \
    -d "{
      \"enabled\": true,
      \"provider\": \"evolution\",
      \"rootNumber\": \"$MASTER_NUMBER\",
      \"rootName\": \"Vulcan Notifications\",
      \"baseUrl\": \"http://evolution:8080\",
      \"instanceName\": \"vulcan-root\",
      \"mockMode\": false,
      \"requireOptIn\": true,
      \"emailFallbackEnabled\": true,
      \"inAppFallbackEnabled\": true
    }" >/dev/null
fi

response="$(curl -fsS "$API_URL/integrations/whatsapp/evolution/qr" \
  -H "Authorization: Bearer $token" \
  -H "X-Tenant-Id: $TENANT_ID")"

status="$(printf "%s" "$response" | jq -r '.status // "unknown"')"
message="$(printf "%s" "$response" | jq -r '.message // ""')"
qr="$(printf "%s" "$response" | jq -r '.qrCode // empty')"

echo "Status: $status"
[ -n "$message" ] && echo "$message"

if [ -z "$qr" ]; then
  echo
  echo "Nenhum QR retornado. Entre como dono em http://localhost:3002 -> Configurações -> WhatsApp."
  exit 0
fi

mkdir -p "$ROOT_DIR/.runtime"
QR_FILE="$ROOT_DIR/.runtime/evolution-qr.png"

if [[ "$qr" == data:image*base64,* ]]; then
  printf "%s" "${qr#*,}" | base64 -d > "$QR_FILE"
  echo "QR salvo em: $QR_FILE"
elif [[ "$qr" =~ ^[A-Za-z0-9+/=]+$ ]] && [ "${#qr}" -gt 120 ]; then
  printf "%s" "$qr" | base64 -d > "$QR_FILE" 2>/dev/null || {
    printf "%s\n" "$qr" > "$ROOT_DIR/.runtime/evolution-qr.txt"
    echo "QR texto salvo em: $ROOT_DIR/.runtime/evolution-qr.txt"
    exit 0
  }
  echo "QR salvo em: $QR_FILE"
else
  printf "%s\n" "$qr" > "$ROOT_DIR/.runtime/evolution-qr.txt"
  echo "QR texto salvo em: $ROOT_DIR/.runtime/evolution-qr.txt"
fi

echo
echo "Abra o QR no navegador/visualizador e escaneie com o WhatsApp do celular:"
echo "  xdg-open $QR_FILE"
echo
echo "Ou use a tela como dono: http://localhost:3002 -> Configurações -> WhatsApp -> Ver QR"
