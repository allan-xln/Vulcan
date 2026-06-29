#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_SOURCE="$ROOT_DIR/agentes/linux/vulcan_agent.py"
INSTALL_DIR="${HOME}/.local/share/vulcan/agent"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/vulcan/agent"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/vulcan-agent"
POLICY_FILE="$CONFIG_DIR/agent-policy.json"
AGENT_TARGET="$INSTALL_DIR/vulcan_agent.py"

mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$STATE_DIR/queue" "$STATE_DIR/logs"
cp "$AGENT_SOURCE" "$AGENT_TARGET"
chmod +x "$AGENT_TARGET"

if [[ -f "$POLICY_FILE" ]]; then
  cp "$POLICY_FILE" "$POLICY_FILE.bak-$(date +%Y%m%d%H%M%S)"
fi

python3 - <<'PY'
import json
import os
from pathlib import Path

config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "vulcan" / "agent"
policy_file = config_dir / "agent-policy.json"
policy = {}
if policy_file.exists():
    try:
        policy = json.loads(policy_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        policy = {}

policy.update(
    {
        "collectAppName": True,
        "collectWindowTitle": True,
        "collectIdleTime": True,
        "collectSessionEvents": True,
        "collectBrowserDomain": True,
        "collectBrowserUrl": True,
        "collectBrowserHistory": True,
        "collectBrowserPageTitle": True,
        "collectProcessList": True,
        "collectSystemMetrics": True,
        "redactSensitiveTerms": True,
        "browserHistoryIntervalSeconds": 300,
        "browserHistoryLookbackMinutes": 120,
        "browserHistoryMaxEvents": 100,
        "syncIntervalSeconds": 30,
        "heartbeatIntervalSeconds": 60,
        "syncBatchSize": 100,
        "httpTimeoutSeconds": 30,
        "offlineQueueEnabled": True,
        "maxOfflineQueueSize": 10000,
        "allowUserPause": False,
        "showTrayStatus": True,
        "privacyMode": "corporate",
        "idleThresholdSeconds": 300,
    }
)
policy_file.parent.mkdir(parents=True, exist_ok=True)
policy_file.write_text(json.dumps(policy, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

systemctl --user daemon-reload || true
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XAUTHORITY XDG_CURRENT_DESKTOP DESKTOP_SESSION XDG_SESSION_TYPE DBUS_SESSION_BUS_ADDRESS || true
systemctl --user restart vulcan-agent.service

"$AGENT_TARGET" heartbeat || true
"$AGENT_TARGET" sync || true
"$AGENT_TARGET" status

echo
echo "Modo corporativo do Vulcan Agent ativado para este usuário."
echo "Logs: journalctl --user -u vulcan-agent.service -f"
