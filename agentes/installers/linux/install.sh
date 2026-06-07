#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/share/vulcan/agent"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/vulcan/agent"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/vulcan-agent"
SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

TENANT_ID="00000000-0000-0000-0000-000000000301"
BACKEND_URL="http://localhost:3001"
ENROLLMENT_TOKEN="vulcan-local-enrollment-token"
LINKED_USER="${USER:-$(id -un)}"
ROLE_LEVEL="Operador"
DEPARTMENT="Operacoes"
MEMBERSHIP_ID=""
COLLECT_WINDOW_TITLE="false"
COLLECT_BROWSER_DOMAIN="false"
COLLECT_BROWSER_URL="false"
COLLECT_PROCESS_LIST="false"
INSTALL_DEPS="false"
DEMO_TEST_MEMBERSHIP_ID="00000000-0000-0000-0000-000000300005"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tenant-id) TENANT_ID="$2"; shift 2 ;;
    --backend-url) BACKEND_URL="$2"; shift 2 ;;
    --enrollment-token) ENROLLMENT_TOKEN="$2"; shift 2 ;;
    --linked-user) LINKED_USER="$2"; shift 2 ;;
    --role-level) ROLE_LEVEL="$2"; shift 2 ;;
    --department) DEPARTMENT="$2"; shift 2 ;;
    --membership-id) MEMBERSHIP_ID="$2"; shift 2 ;;
    --collect-window-title) COLLECT_WINDOW_TITLE="true"; shift ;;
    --collect-browser-domain) COLLECT_BROWSER_DOMAIN="true"; shift ;;
    --collect-browser-url) COLLECT_BROWSER_URL="true"; shift ;;
    --collect-process-list) COLLECT_PROCESS_LIST="true"; shift ;;
    --install-deps) INSTALL_DEPS="true"; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$MEMBERSHIP_ID" && "$TENANT_ID" == "00000000-0000-0000-0000-000000000301" && "$LINKED_USER" == "teste" ]]; then
  MEMBERSHIP_ID="$DEMO_TEST_MEMBERSHIP_ID"
fi

if [[ "$INSTALL_DEPS" == "true" ]]; then
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y xdotool wmctrl xprintidle
  fi
fi

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$STATE_DIR/queue" "$STATE_DIR/logs" "$SYSTEMD_DIR"
cp "$SCRIPT_DIR/vulcan_agent.py" "$INSTALL_DIR/vulcan_agent.py"
chmod +x "$INSTALL_DIR/vulcan_agent.py"

CONFIG_ARGS=(
  write-config
  --tenant-id "$TENANT_ID"
  --backend-url "$BACKEND_URL"
  --enrollment-token "$ENROLLMENT_TOKEN"
  --linked-user "$LINKED_USER"
  --role-level "$ROLE_LEVEL"
  --department "$DEPARTMENT"
)

if [[ -n "$MEMBERSHIP_ID" ]]; then
  CONFIG_ARGS+=(--membership-id "$MEMBERSHIP_ID")
fi
if [[ "$COLLECT_WINDOW_TITLE" == "true" ]]; then
  CONFIG_ARGS+=(--collect-window-title)
fi
if [[ "$COLLECT_BROWSER_DOMAIN" == "true" ]]; then
  CONFIG_ARGS+=(--collect-browser-domain)
fi
if [[ "$COLLECT_BROWSER_URL" == "true" ]]; then
  CONFIG_ARGS+=(--collect-browser-url)
fi
if [[ "$COLLECT_PROCESS_LIST" == "true" ]]; then
  CONFIG_ARGS+=(--collect-process-list)
fi

"$INSTALL_DIR/vulcan_agent.py" "${CONFIG_ARGS[@]}" >/dev/null

cat > "$SYSTEMD_DIR/vulcan-agent.service" <<UNIT
[Unit]
Description=Vulcan Linux Agent
After=network-online.target graphical-session.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/vulcan_agent.py run
Restart=always
RestartSec=8
Environment=PYTHONUNBUFFERED=1
Environment=VULCAN_AGENT_CONFIG=$CONFIG_DIR/config.json

[Install]
WantedBy=default.target
UNIT

systemctl --user daemon-reload
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XAUTHORITY XDG_CURRENT_DESKTOP DESKTOP_SESSION XDG_SESSION_TYPE DBUS_SESSION_BUS_ADDRESS || true
systemctl --user enable --now vulcan-agent.service

echo "Vulcan Linux Agent installed."
echo "Status: systemctl --user status vulcan-agent.service --no-pager"
echo "Logs: journalctl --user -u vulcan-agent.service -f"
