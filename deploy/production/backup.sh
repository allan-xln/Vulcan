#!/usr/bin/env bash

set -euo pipefail
umask 077

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DEPLOY_DIR/.env.production"
PASSPHRASE_FILE="${BACKUP_ENCRYPTION_PASSPHRASE_FILE:-$DEPLOY_DIR/secrets/backup_encryption_passphrase}"
BACKUP_ROOT="${VULCAN_BACKUP_ROOT:-$DEPLOY_DIR/backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_ROOT"
chmod 0700 "$BACKUP_ROOT"
staging="$(mktemp -d "$BACKUP_ROOT/.vulcan-backup-${timestamp}.XXXXXX")"

cleanup() {
  rm -rf -- "$staging"
}
trap cleanup EXIT

if [[ ! -s "$PASSPHRASE_FILE" ]]; then
  echo "Crie um passphrase forte em $PASSPHRASE_FILE com permissão 0600." >&2
  exit 1
fi

mkdir -p "$staging/database" "$staging/config" "$staging/volumes"
chmod 0700 "$BACKUP_ROOT" "$staging"
compose=(docker compose --env-file "$ENV_FILE" -f "$DEPLOY_DIR/compose.yml")

"${compose[@]}" exec -T db pg_dump -U postgres -d vulcan -Fc > "$staging/database/vulcan.dump"
"${compose[@]}" exec -T db pg_dumpall -U postgres --globals-only > "$staging/database/postgres-globals.sql"
"${compose[@]}" exec -T evolution-db pg_dump -U evolution -d evolution -Fc > "$staging/database/evolution.dump"

for volume in \
  vulcan-production-runtime \
  vulcan-production-evolution-instances \
  vulcan-production-evolution-redis; do
  docker run --rm \
    -v "$volume:/volume:ro" \
    alpine:3.22 tar -C /volume -czf - . > "$staging/volumes/$volume.tar.gz"
done

cp "$ENV_FILE" "$staging/config/.env.production"
tar -C "$DEPLOY_DIR" -czf "$staging/config/secrets.tar.gz" secrets
find "$staging" -type f -exec chmod 0600 {} +
(cd "$staging" && find . -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)

archive="$BACKUP_ROOT/vulcan-production-$timestamp.tar.gz.enc"
tar -C "$staging" -czf - . | openssl enc -aes-256-cbc -pbkdf2 -salt \
  -pass "file:$PASSPHRASE_FILE" -out "$archive"
sha256sum "$archive" > "$archive.sha256"
chmod 0600 "$archive" "$archive.sha256"

echo "Backup criptografado criado: $archive"
