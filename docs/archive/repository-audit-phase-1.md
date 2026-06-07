# Repository Audit Before Clean Phase 1

## Present
- Monorepo root files and workspace config existed.
- A minimal Next.js app existed.
- A minimal FastAPI service existed.
- Basic architecture, roadmap and acceptance-criteria docs existed.
- Base `docker-compose.yml` existed for Redis, ClickHouse, Ollama and Alloy.

## Missing
1. `pnpm-lock.yaml` was incorrectly ignored, which prevents a reproducible Node workspace baseline.
2. The required frontend stack baseline was incomplete:
   - no shadcn/ui-compatible setup
   - no SWR
   - no charting library
3. The required test stack baseline was incomplete:
   - no Vitest config or tests
   - no Playwright config or e2e spec
4. There was no CI workflow to verify the repo on push and pull request.
5. There was no reserved layout for Supabase assets or the Windows-first agent collector.
6. Verification only covered lint, TypeScript and pytest; it did not prove frontend unit tests or production build integrity.

## Resolution in this phase
- Commit the lockfile.
- Add the missing frontend baseline pieces.
- Add Vitest, Playwright and CI skeletons.
- Add reserved directories for Supabase and the agent collector.
- Expand verification to include frontend unit tests and build.
