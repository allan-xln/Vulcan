#!/usr/bin/env bash

set -euo pipefail
umask 077

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="$DEPLOY_DIR/secrets"
mkdir -p "$SECRETS_DIR"
chmod 0700 "$SECRETS_DIR"

generate_hex() {
  local target="$1"
  local bytes="$2"
  if [[ ! -s "$target" ]]; then
    openssl rand -hex "$bytes" > "$target"
  fi
  chmod 0600 "$target"
}

generate_password() {
  local target="$1"
  if [[ ! -s "$target" ]]; then
    openssl rand -base64 36 | tr -d '\n' > "$target"
  fi
  chmod 0600 "$target"
}

ensure_runtime_secret() {
  local target="$1"
  if [[ ! -e "$target" ]]; then
    install -m 0600 /dev/null "$target"
  fi
  chmod 0600 "$target"
}

generate_hex "$SECRETS_DIR/postgres_password" 32
generate_hex "$SECRETS_DIR/auth_signing_key" 48
generate_hex "$SECRETS_DIR/agent_enrollment_token" 32
generate_password "$SECRETS_DIR/root_initial_password"
generate_password "$SECRETS_DIR/ers_admin_initial_password"
generate_password "$SECRETS_DIR/wallboard_initial_password"
generate_hex "$SECRETS_DIR/evolution_db_password" 32
generate_hex "$SECRETS_DIR/evolution_api_key" 32
generate_hex "$SECRETS_DIR/evolution_webhook_token" 32
ensure_runtime_secret "$SECRETS_DIR/unifi_username"
ensure_runtime_secret "$SECRETS_DIR/unifi_password"
ensure_runtime_secret "$SECRETS_DIR/proxmox_username"
ensure_runtime_secret "$SECRETS_DIR/proxmox_password"

evolution_password="$(<"$SECRETS_DIR/evolution_db_password")"
evolution_api_key="$(<"$SECRETS_DIR/evolution_api_key")"
{
  printf 'DATABASE_CONNECTION_URI=postgresql://evolution:%s@evolution-db:5432/evolution?schema=public\n' "$evolution_password"
  printf 'AUTHENTICATION_API_KEY=%s\n' "$evolution_api_key"
} > "$SECRETS_DIR/evolution.env"
chmod 0600 "$SECRETS_DIR/evolution.env"

if ! command -v setfacl >/dev/null 2>&1; then
  echo "setfacl é obrigatório para entregar secrets aos containers sem executar como root." >&2
  exit 1
fi

grant_read() {
  local target="$1"
  shift
  setfacl -b "$target"
  chmod 0600 "$target"
  setfacl -m "g::---,m::r--" "$target"
  local uid
  for uid in "$@"; do
    setfacl -m "u:${uid}:r--" "$target"
  done
}

grant_read "$SECRETS_DIR/postgres_password" 10001 10002
grant_read "$SECRETS_DIR/auth_signing_key" 10001
grant_read "$SECRETS_DIR/agent_enrollment_token" 10001
grant_read "$SECRETS_DIR/root_initial_password" 10001
grant_read "$SECRETS_DIR/ers_admin_initial_password" 10001
grant_read "$SECRETS_DIR/wallboard_initial_password" 10001
grant_read "$SECRETS_DIR/evolution_api_key" 10001
grant_read "$SECRETS_DIR/evolution_webhook_token" 10001
grant_read "$SECRETS_DIR/unifi_username" 10001
grant_read "$SECRETS_DIR/unifi_password" 10001
grant_read "$SECRETS_DIR/proxmox_username" 10001
grant_read "$SECRETS_DIR/proxmox_password" 10001

echo "Secrets de produção prontos em diretório protegido: $SECRETS_DIR"
echo "Os valores não foram exibidos e não devem ser adicionados ao Git."
