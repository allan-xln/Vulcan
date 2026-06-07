# Acceptance Criteria

## Phase 1 must satisfy
1. The repository uses a documented monorepo structure with `apps`, `packages`, `services`, `infra`, `docs` and `scripts`.
2. A minimal Next.js app and a minimal FastAPI service exist with executable startup commands.
3. `.env.example`, bootstrap scripts and verification scripts exist and are consistent with the file layout.
4. `docker-compose.yml` defines the local analytics and AI dependencies required for later phases.
5. The required frontend baseline is present: Next.js, TypeScript, Tailwind, shadcn/ui-compatible component setup, SWR and a charting library.
6. Unit-test and end-to-end test baselines exist with Vitest and Playwright.
7. A GitHub Actions workflow verifies the Phase 1 baseline.
8. The architecture, repository conventions and phased roadmap are documented.
9. The repo does not claim unsupported spyware-like capabilities.
10. The current foundation is small enough to review and extend incrementally.
