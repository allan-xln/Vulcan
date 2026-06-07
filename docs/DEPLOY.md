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

## One Database Requirement

Production deployment must use one logical database for business data. Additional caches or queues may be introduced later, but they must not become tenant-specific databases or sources of truth without a formal architecture review.
