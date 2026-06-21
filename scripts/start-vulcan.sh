#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
LOG_DIR="$RUNTIME_DIR/logs"
PID_DIR="$RUNTIME_DIR/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi
if [ -f "$ROOT_DIR/infra/evolution/.env" ]; then
  set -a
  source "$ROOT_DIR/infra/evolution/.env"
  set +a
fi

export EVOLUTION_ENABLED="${EVOLUTION_ENABLED:-true}"
export EVOLUTION_BASE_URL="${EVOLUTION_BASE_URL:-http://127.0.0.1:8080}"
export EVOLUTION_INSTANCE_NAME="${EVOLUTION_INSTANCE_NAME:-vulcan-root}"
export EVOLUTION_WEBHOOK_URL="${EVOLUTION_WEBHOOK_URL:-http://host.docker.internal:3001/integrations/whatsapp/evolution/webhook}"
export WHATSAPP_PROVIDER="${WHATSAPP_PROVIDER:-evolution}"
export ROOT_WHATSAPP_PROVIDER="${ROOT_WHATSAPP_PROVIDER:-evolution}"
export WHATSAPP_ENABLE_UNOFFICIAL_PROVIDER="${WHATSAPP_ENABLE_UNOFFICIAL_PROVIDER:-true}"
export WHATSAPP_REQUIRE_OPT_IN="${WHATSAPP_REQUIRE_OPT_IN:-true}"
export VULCAN_API_RELOAD=false

process_alive() {
  local pid_file="$1"
  [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

start_process() {
  local name="$1"
  shift
  local pid_file="$PID_DIR/$name.pid"
  if process_alive "$pid_file"; then
    echo "$name já está rodando (PID $(cat "$pid_file"))."
    return
  fi
  rm -f "$pid_file"
  setsid nohup "$@" >> "$LOG_DIR/$name.log" 2>&1 < /dev/null &
  local pid=$!
  echo "$pid" > "$pid_file"
  sleep 1
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "$name falhou ao iniciar. Veja $LOG_DIR/$name.log" >&2
    tail -n 40 "$LOG_DIR/$name.log" >&2 || true
    exit 1
  fi
  echo "$name iniciado (PID $pid)."
}

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "Ambiente Python ausente. Rode ./scripts/bootstrap.sh." >&2
  exit 1
fi

if command -v ss >/dev/null 2>&1 && ss -ltnH "sport = :${LOCAL_API_PORT:-3001}" | grep -q .; then
  if ! curl -fsS "http://127.0.0.1:${LOCAL_API_PORT:-3001}/health" >/dev/null; then
    echo "Porta ${LOCAL_API_PORT:-3001} ocupada por outro processo." >&2
    exit 1
  fi
  echo "backend já responde em ${LOCAL_API_PORT:-3001}."
else
  start_process backend "$ROOT_DIR/scripts/run-api.sh"
fi

FRONTEND_PORT="${FRONTEND_PORT:-3002}"
if command -v ss >/dev/null 2>&1 && ss -ltnH "sport = :$FRONTEND_PORT" | grep -q .; then
  echo "frontend já possui processo na porta $FRONTEND_PORT."
else
  start_process frontend corepack pnpm --dir "$ROOT_DIR/frontend/web" dev --hostname 0.0.0.0 --port "$FRONTEND_PORT"
fi
echo "$FRONTEND_PORT" > "$RUNTIME_DIR/frontend-port"

start_process whatsapp-worker "$ROOT_DIR/scripts/run-whatsapp-worker.sh"

echo "Backend: http://127.0.0.1:${LOCAL_API_PORT:-3001}"
echo "Frontend: http://127.0.0.1:$FRONTEND_PORT"
