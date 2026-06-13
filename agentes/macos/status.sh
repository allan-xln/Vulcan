#!/usr/bin/env bash
set -euo pipefail

BIN="$HOME/Library/Application Support/Vulcan/Agent/vulcan_macos_agent.py"
if [[ ! -x "$BIN" ]]; then
  echo "Vulcan macOS Agent nao instalado."
  exit 1
fi

"$BIN" status
launchctl list | grep -F "com.lanfuture.vulcan.agent" || true
