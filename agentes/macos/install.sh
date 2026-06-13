#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:3001}"
TENANT_ID="${TENANT_ID:-00000000-0000-0000-0000-000000000301}"
ENROLLMENT_TOKEN="${ENROLLMENT_TOKEN:-vulcan-local-enrollment-token}"
MEMBERSHIP_ID="${MEMBERSHIP_ID:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-url) BACKEND_URL="$2"; shift 2 ;;
    --tenant-id) TENANT_ID="$2"; shift 2 ;;
    --enrollment-token) ENROLLMENT_TOKEN="$2"; shift 2 ;;
    --membership-id) MEMBERSHIP_ID="$2"; shift 2 ;;
    *) echo "Argumento desconhecido: $1" >&2; exit 2 ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/Library/Application Support/Vulcan/Agent"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/com.lanfuture.vulcan.agent.plist"

mkdir -p "$BIN_DIR" "$PLIST_DIR"
cp "$ROOT_DIR/vulcan_macos_agent.py" "$BIN_DIR/vulcan_macos_agent.py"
chmod +x "$BIN_DIR/vulcan_macos_agent.py"

"$BIN_DIR/vulcan_macos_agent.py" configure \
  --backend-url "$BACKEND_URL" \
  --tenant-id "$TENANT_ID" \
  --enrollment-token "$ENROLLMENT_TOKEN" \
  ${MEMBERSHIP_ID:+--membership-id "$MEMBERSHIP_ID"}

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.lanfuture.vulcan.agent</string>
  <key>ProgramArguments</key>
  <array>
    <string>$BIN_DIR/vulcan_macos_agent.py</string>
    <string>run</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/VulcanAgent/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/VulcanAgent/launchd.err.log</string>
</dict>
</plist>
PLIST

launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl load "$PLIST_PATH"
"$BIN_DIR/vulcan_macos_agent.py" enroll || true
"$BIN_DIR/vulcan_macos_agent.py" status
