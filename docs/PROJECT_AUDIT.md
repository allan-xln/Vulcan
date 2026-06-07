# Project Audit

## Source Found

The active source was found in a previous temporary development tree and was consolidated into `/home/allan/Dev/Vulcan`.

## Main Components Found

- Next.js frontend.
- FastAPI ingestion gateway.
- FastAPI query API.
- FastAPI AI API.
- Python background jobs.
- Supabase/PostgreSQL migrations and validation SQL.
- Placeholder agent collector documentation.
- Shared TypeScript domain and operational event schema packages.

## Duplicates And Dead Artifacts

Removed from the active Vulcan tree:

- `node_modules`
- `.venv`
- `build`
- `.pytest_cache`
- `*.egg-info`
- generated package build outputs

## Architectural Issues Found

- Product identity was split across temporary development names and telemetry language.
- Docker stack included ClickHouse and Redis despite the one-database requirement.
- Jobs could run with `tenant_id = null`.
- AI API was only a health check and did not call GPT.
- Supabase platform requirements were undocumented.
- Enterprise documentation was incomplete.

## Actions Taken

- Created `/home/allan/Dev/Vulcan`.
- Reorganized the monorepo.
- Added hybrid GPT + Llama integration surface.
- Updated multi-tenant job and run-table constraints.
- Created enterprise documentation.
