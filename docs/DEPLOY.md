# Deploy

## Local

```bash
./scripts/bootstrap.sh
corepack pnpm supabase:validate
corepack pnpm supabase:migrate
corepack pnpm dev
```

## Services

```bash
./scripts/run-ingestion-gateway.sh
./scripts/run-query-api.sh
./scripts/run-ai-api.sh
```

## Production Requirements

- managed PostgreSQL or Supabase database
- Supabase Auth configured for production domains
- Supabase Storage buckets and RLS policies
- secret manager
- CI/CD pipeline
- HTTPS ingress
- JWT validation
- tenant-aware observability
- backup and restore policy
- migration process with rollback plan

## Domains And CORS

Production must set explicit origins. Do not use `*` in production.

```env
API_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3002,http://localhost:3102,http://127.0.0.1:3000,http://127.0.0.1:3002,http://127.0.0.1:3102,https://vulcan.lanfuture.dev,https://vulcan-demo.lanfuture.dev,https://vulcan-staging.lanfuture.dev
NEXT_PUBLIC_API_URL=https://api.vulcan.lanfuture.dev
```

Vercel preview support should use an exact origin from `VERCEL_URL` or `NEXT_PUBLIC_VERCEL_URL`, not an open wildcard.

Commercial target:

- `vulcan.lanfuture.dev`: real product/demo environment.
- landing `/vulcan`: should point to the real Vulcan environment when deploy is ready.

## One Database Requirement

Production deployment must use one logical database for business data. Additional caches or queues may be introduced later, but they must not become tenant-specific databases or sources of truth without a formal architecture review.
