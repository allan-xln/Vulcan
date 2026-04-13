# Local Development Runbook

## Goal
Run the current repository locally with:
- the web app
- the AI API
- a local Postgres database that is compatible enough to validate Phase 2 migrations and RLS

## Required local installs
- `docker` with Compose support
- `node` 22.x
- `pnpm` 10.x
- `python3` 3.10+
- `psql`

## One-time bootstrap
```bash
cp .env.example .env
./scripts/bootstrap.sh
```

## Start the local database
```bash
./scripts/db-up.sh
```

## Apply Phase 2
```bash
./scripts/apply-phase2-sql.sh
```

## Verify Phase 2
```bash
./scripts/verify-phase2.sh
```

## Apply Phase 3
```bash
./scripts/apply-phase3-sql.sh
```

## Verify Phase 3
```bash
./scripts/verify-phase3.sh
```

## Apply Phase 4
```bash
./scripts/apply-phase4-sql.sh
```

## Verify Phase 4
```bash
./scripts/verify-phase4.sh
```

## Run the normalization job
```bash
./scripts/run-normalization-job.sh --batch-limit 500
```

## Apply Phase 5
```bash
./scripts/apply-phase5-sql.sh
```

## Verify Phase 5
```bash
./scripts/verify-phase5.sh
```

## Run the operational facts job
```bash
./scripts/run-operational-facts-job.sh
```

## Apply Phase 6
```bash
./scripts/apply-phase6-sql.sh
```

## Verify Phase 6
```bash
./scripts/verify-phase6.sh
```

## Run the daily metrics job
```bash
./scripts/run-daily-metrics-job.sh
```

## Verify Phase 7
```bash
./scripts/verify-phase7.sh
```

## Run the query API
```bash
./scripts/run-query-api.sh
```

## Run the web app
```bash
pnpm dev:web
```

The web app will be available at `http://127.0.0.1:3000`.

## Run the AI API
```bash
./scripts/run-ai-api.sh
```

The AI API health endpoint will be available at `http://127.0.0.1:8000/health`.

## Run the ingestion gateway
```bash
./scripts/run-ingestion-gateway.sh
```

The ingestion gateway health endpoint will be available at `http://127.0.0.1:8010/health`.

## Helpful database commands
Tail logs:
```bash
./scripts/db-logs.sh
```

Reset only the local database container and volume:
```bash
./scripts/db-reset.sh
```

Stop only the local database container:
```bash
./scripts/db-down.sh
```

## Notes
- The local database path uses a minimal compatibility layer for `auth.users`, `auth.uid()` and the `authenticated` role so Phase 2 can be validated without a full Supabase stack.
- This local path is for schema and RLS validation only. It is not a full Supabase replacement.
