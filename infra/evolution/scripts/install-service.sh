#!/usr/bin/env bash

set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

require_docker
ensure_env

ROOT_DIR="$(cd "$EVOLUTION_DIR/../.." && pwd)"
SERVICE_SOURCE="$EVOLUTION_DIR/systemd/vulcan-evolution.service"
SERVICE_TARGET="/etc/systemd/system/vulcan-evolution.service"
RUN_USER="${SUDO_USER:-$USER}"
RUN_GROUP="$(id -gn "$RUN_USER")"
TEMP_SERVICE="$(mktemp)"
trap 'rm -f "$TEMP_SERVICE"' EXIT

sed \
  -e "s|__VULCAN_ROOT__|$ROOT_DIR|g" \
  -e "s|__VULCAN_USER__|$RUN_USER|g" \
  -e "s|__VULCAN_GROUP__|$RUN_GROUP|g" \
  "$SERVICE_SOURCE" > "$TEMP_SERVICE"

sudo install -m 0644 "$TEMP_SERVICE" "$SERVICE_TARGET"
sudo systemctl daemon-reload
sudo systemctl enable --now vulcan-evolution.service
sudo systemctl status vulcan-evolution.service --no-pager
echo "Autostart instalado. QR Code: Configurações > WhatsApp no Vulcan."
