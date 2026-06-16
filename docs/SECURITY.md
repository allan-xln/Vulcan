# Security

## Security Principles

- No spyware behavior.
- No password collection.
- No keystroke collection.
- No clipboard collection.
- No screenshot collection.
- No indiscriminate private-content capture.
- Tenant isolation is mandatory.
- Auditability is mandatory for sensitive business data.

## Authentication And Authorization

Current local development uses `admin/admin` as a fallback. Production must use Supabase Auth JWT validation plus PostgreSQL RLS.

Authorization must always resolve:

- user identity
- tenant membership
- tenant role
- permission
- data scope

## Secrets

Required secrets must live in environment variables or a managed secret store, never in source files.

Key secrets:

- `DATABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OPENAI_API_KEY`
- Supabase service-role and secret keys
- ingestion API keys

The Settings screen returns only secret status (`configurado`, `requer credencial`, `mock explicito`). It never returns actual secret values and `PUT /settings/{section}` rejects `secret` and `readonly` fields.

## Settings Security

Configuration writes are restricted to tenant/admin scope. Operators can read allowed state but cannot mutate tenant settings. Every successful settings write records `settings.updated` in `audit_logs`.

## AI Safety

GPT must receive only structured operational evidence. It must not receive raw passwords, keystrokes, screenshots, clipboard content, or cross-tenant data.
