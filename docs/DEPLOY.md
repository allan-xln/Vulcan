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

## Release de produção self-hosted

O endereço oficial é `192.168.200.4:8099`, mas o runtime fica isolado no host Linux
`192.168.200.160`. O servidor 4 é controlador de domínio/DNS e não recebe runtime, banco
ou containers do Vulcan. O runbook autoritativo está em
`docs/PRODUCTION_ERS_192_168_200_4.md`.

A release autocontida fica em `dist/vulcan-<versão>-linux-amd64.tar.gz` e contém somente
imagens de runtime, Compose, migrations, scripts, manifests, checksums e SBOM. Ela não
contém `.git`, árvore de código, testes nem secrets.

```bash
cd /home/allan/Documentos/ProjetosLanFuture/Vulcan
PATH="$PWD/.tools/syft/bin:$PATH" ./scripts/build-production-release.sh 0.3.4
sha256sum -c dist/vulcan-0.3.4-linux-amd64.tar.gz.sha256
```

No host Linux isolado:

```bash
tar -xzf vulcan-0.3.4-linux-amd64.tar.gz
cd vulcan-0.3.4-linux-amd64
cp .env.production.example .env.production
chmod 0600 .env.production
# Revisar URL, versão, commit e build antes do primeiro start.
./deploy.sh --restore-dir /caminho/privado/backup-validado
./healthcheck.sh
```

O Compose publica somente o proxy de borda. PostgreSQL, Evolution, Redis, API e frontend
permanecem nas redes Docker internas. `discovery` usa o profile `network`, inicia
desabilitado e exige aprovação explícita das redes do site.

O corte reutiliza o encaminhamento exclusivo `192.168.200.4:8099` para
`192.168.200.160:8099`. Não altere AD, DNS ou outros listeners do controlador de domínio.

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
