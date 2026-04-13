# Query API

Tenant-scoped read API for operational metrics and facts.

## Current scope
- daily user operational metrics
- session slices
- idle windows
- application usage facts

## Auth assumption
- local/dev requests send `X-User-Id`
- the API verifies active membership in the requested tenant
- the database read path also runs with Postgres `authenticated` role and `request.jwt.claim.sub` so RLS remains enforced

## Local run
```bash
source .env
source .venv/bin/activate
uvicorn app.main:app --reload --host "${QUERY_API_HOST:-0.0.0.0}" --port "${QUERY_API_PORT:-8020}" --app-dir services/query-api
```

