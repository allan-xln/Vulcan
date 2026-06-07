#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

if [ -z "${SUPABASE_URL:-}" ]; then
  echo "SUPABASE_URL is missing" >&2
  exit 1
fi

if [ -z "${SUPABASE_ANON_KEY:-${NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY:-}}" ]; then
  echo "SUPABASE_ANON_KEY or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY is missing" >&2
  exit 1
fi

API_KEY="${SUPABASE_ANON_KEY:-$NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY}"
REST_URL="${SUPABASE_REST_URL:-${SUPABASE_URL%/}/rest/v1}"

curl -fsS "${SUPABASE_URL%/}/auth/v1/settings" \
  -H "apikey: $API_KEY" \
  >/dev/null

REST_STATUS="$(curl -s -o /dev/null -w '%{http_code}' "$REST_URL/tenants?select=id&limit=1" \
  -H "apikey: $API_KEY" \
  -H "Authorization: Bearer $API_KEY")"

case "$REST_STATUS" in
  200|401|404) ;;
  *)
    echo "Unexpected Supabase REST status: $REST_STATUS" >&2
    exit 1
    ;;
esac

if [ -n "${DATABASE_URL:-}" ] && command -v psql >/dev/null 2>&1; then
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -qAt -c "select 'postgres-ok';" >/dev/null
fi

echo "Supabase connection validated"
