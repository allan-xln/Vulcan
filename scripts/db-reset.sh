#!/usr/bin/env bash

set -euo pipefail

docker compose stop db || true
docker compose rm -fsv db || true
docker volume rm telemetry-saas-lab_postgres-data >/dev/null 2>&1 || true
docker compose up -d db
