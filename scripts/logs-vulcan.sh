#!/usr/bin/env bash

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/.runtime/logs"
mkdir -p "$LOG_DIR"

if [ "${1:-}" = "--follow" ] || [ "${1:-}" = "-f" ]; then
  touch "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log" "$LOG_DIR/whatsapp-worker.log"
  exec tail -n 100 -F "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log" "$LOG_DIR/whatsapp-worker.log"
fi

for name in backend frontend whatsapp-worker; do
  echo "===== $name ====="
  tail -n 100 "$LOG_DIR/$name.log" 2>/dev/null || echo "sem logs"
done
