#!/usr/bin/env bash

set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DEPLOY_DIR/.env.production"

if [[ "${1:-}" != "--initial" || -z "${2:-}" || ! -d "${2:-}" ]]; then
  echo "Uso seguro: $0 --initial /diretorio/backup-descriptografado" >&2
  exit 1
fi

BACKUP_DIR="$(cd "$2" && pwd)"
VULCAN_DUMP="$BACKUP_DIR/database/vulcan.dump"
EVOLUTION_DUMP="$BACKUP_DIR/database/evolution.dump"
GLOBALS_SQL="$BACKUP_DIR/database/postgres-globals.sql"

for required_file in "$VULCAN_DUMP" "$EVOLUTION_DUMP" "$GLOBALS_SQL"; do
  if [[ ! -r "$required_file" ]]; then
    echo "Backup obrigatório ausente: $required_file" >&2
    exit 1
  fi
done

compose=(docker compose --env-file "$ENV_FILE" -f "$DEPLOY_DIR/compose.yml")
tenant_table="$("${compose[@]}" exec -T db psql -U postgres -d vulcan -Atqc \
  "select coalesce(to_regclass('public.tenants')::text, '')")"
tenant_count="0"
if [[ -n "$tenant_table" ]]; then
  tenant_count="$("${compose[@]}" exec -T db psql -U postgres -d vulcan -Atqc \
    "select count(*) from public.tenants")"
fi
if [[ "$tenant_count" != "0" ]]; then
  echo "Restore inicial recusado: o destino já possui $tenant_count tenant(s)." >&2
  exit 1
fi

"${compose[@]}" stop backend whatsapp-worker frontend edge >/dev/null 2>&1 || true
"${compose[@]}" exec -T db psql -U postgres -d postgres < "$GLOBALS_SQL" >/dev/null 2>&1 || true
"${compose[@]}" exec -T db sh -ec \
  'database_password="$(cat /run/secrets/postgres_password)"; psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "alter role postgres password '\''${database_password}'\''" >/dev/null'
"${compose[@]}" exec -T db pg_restore \
  -U postgres -d vulcan --clean --if-exists --no-owner --no-privileges < "$VULCAN_DUMP"
"${compose[@]}" exec -T evolution-db pg_restore \
  -U evolution -d evolution --clean --if-exists --no-owner --no-privileges < "$EVOLUTION_DUMP"

echo "Restore inicial concluído. As migrations e as validações ainda precisam ser executadas."
