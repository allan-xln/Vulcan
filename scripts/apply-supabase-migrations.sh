#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$ROOT_DIR/.env" ]; then
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" == \#* || "$key" != *[A-Za-z0-9_]* ]] && continue
    if [ -z "${!key:-}" ]; then
      value="${value%\"}"
      value="${value#\"}"
      value="${value%\'}"
      value="${value#\'}"
      export "$key=$value"
    fi
  done < "$ROOT_DIR/.env"
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required to apply Supabase migrations" >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is required to apply Supabase migrations" >&2
  exit 1
fi

for migration in "$ROOT_DIR"/database/supabase/migrations/*.sql; do
  echo "Applying $(basename "$migration")"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$migration" >/dev/null
done

echo "Supabase migrations applied"
