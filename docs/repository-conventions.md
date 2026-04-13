# Repository Conventions

## Structure
- `apps/`: user-facing applications
- `packages/`: shared TypeScript packages with explicit ownership
- `services/`: backend and AI services
- `infra/`: local infrastructure and deployment assets
- `docs/`: architecture, roadmap and operating rules
- `scripts/`: bootstrap and verification scripts

## Engineering rules
- TypeScript runs in strict mode.
- Keep `pnpm-lock.yaml` committed.
- Shared packages must expose explicit public entrypoints.
- New services need a health endpoint and a local test on creation.
- Auditability is required for any write path.
- Metrics and scores must document formula, source and tenant scope.
- Avoid abstractions until at least two concrete consumers need them.

## Naming
- Use kebab-case for folders.
- Use `tenant_id` consistently across schemas, payloads and storage keys.
- Prefer explicit suffixes like `*-api`, `*-gateway`, `*-worker`.

## Review bar
- Every phase must leave the repo runnable or statically verifiable.
- Security decisions belong in docs before broad feature implementation.
- No hidden data capture, no silent background collection and no unverifiable AI claims.
