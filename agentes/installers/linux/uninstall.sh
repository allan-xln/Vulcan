#!/usr/bin/env bash
set -euo pipefail

PURGE="false"
if [[ "${1:-}" == "--purge" ]]; then
  PURGE="true"
fi

SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
systemctl --user disable --now vulcan-agent.service 2>/dev/null || true
rm -f "$SYSTEMD_DIR/vulcan-agent.service"
systemctl --user daemon-reload

if [[ "$PURGE" == "true" ]]; then
  rm -rf "$HOME/.local/share/vulcan/agent" "${XDG_CONFIG_HOME:-$HOME/.config}/vulcan/agent" "${XDG_STATE_HOME:-$HOME/.local/state}/vulcan-agent"
fi

echo "Vulcan Linux Agent uninstalled."
