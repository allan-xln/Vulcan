#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM_DATABASE_URL="${VULCAN_PLATFORM_DATABASE_URL:-postgresql://postgres:postgres@127.0.0.1:55432/vulcan}"

psql "$PLATFORM_DATABASE_URL" \
  -v ON_ERROR_STOP=1 \
  -f "$ROOT_DIR/database/supabase/validation/007_platform_expansion_checks.sql"

echo "Vulcan platform expansion validation passed"
