#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

if command -v pnpm >/dev/null 2>&1; then
  PNPM_CMD=(pnpm)
elif command -v corepack >/dev/null 2>&1; then
  PNPM_CMD=(corepack pnpm)
else
  echo "pnpm or corepack is required" >&2
  exit 1
fi

cleanup() {
  jobs -p | xargs -r kill
}

port_is_busy() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltnH "sport = :$port" | grep -q .
    return
  fi
  return 1
}

choose_frontend_port() {
  if [ -n "${FRONTEND_PORT:-}" ]; then
    echo "$FRONTEND_PORT"
    return
  fi

  for port in 3000 3002 3003 3004; do
    if ! port_is_busy "$port"; then
      echo "$port"
      return
    fi
  done

  echo "No available frontend port found in 3000, 3002, 3003, 3004." >&2
  exit 1
}

trap cleanup EXIT INT TERM

FRONTEND_PORT="$(choose_frontend_port)"

"$ROOT_DIR/scripts/run-api.sh" &
"${PNPM_CMD[@]}" --dir "$ROOT_DIR/frontend/web" dev --hostname 0.0.0.0 --port "$FRONTEND_PORT" &

wait
