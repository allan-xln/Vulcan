#!/usr/bin/env bash
set -euo pipefail

AGENT="${HOME}/.local/share/vulcan/agent/vulcan_agent.py"
if [[ ! -x "$AGENT" ]]; then
  echo "Vulcan Linux Agent is not installed at $AGENT" >&2
  exit 1
fi

"$AGENT" status
systemctl --user status vulcan-agent.service --no-pager || true
