#!/usr/bin/env bash
set -euo pipefail

PLIST="$HOME/Library/LaunchAgents/com.lanfuture.vulcan.agent.plist"
launchctl unload "$PLIST" >/dev/null 2>&1 || true
rm -f "$PLIST"

if [[ "${1:-}" == "--purge" ]]; then
  rm -rf "$HOME/Library/Application Support/Vulcan/Agent" "$HOME/Library/Logs/VulcanAgent"
fi

echo "Vulcan macOS Agent removido."
