# Phase 7 Read API Foundation

## Goal
Expose the validated deterministic pipeline through a tenant-scoped read API for the web app.

## Endpoints
- `GET /v1/daily-user-operational-metrics`
- `GET /v1/session-slices`
- `GET /v1/idle-windows`
- `GET /v1/application-usage-facts`

## Auth and scope
- Requests send `X-User-Id`.
- `tenantId` is mandatory in the query string.
- The API verifies an active membership in the requested tenant.
- The database read path then sets the Postgres role to `authenticated` and sets `request.jwt.claim.sub`, so RLS remains active.

## Filters
- `tenantId` required
- `dateFrom` optional
- `dateTo` optional
- `workstationId` optional
- `username` optional
- `limit` optional, default `50`, max `200`
- `offset` optional, default `0`

## Example queries
```bash
curl "http://127.0.0.1:8020/v1/daily-user-operational-metrics?tenantId=00000000-0000-0000-0000-000000000301" \
  -H "X-User-Id: 11111111-1111-1111-1111-111111111111"

curl "http://127.0.0.1:8020/v1/session-slices?tenantId=00000000-0000-0000-0000-000000000301&dateFrom=2026-04-12&dateTo=2026-04-12" \
  -H "X-User-Id: 11111111-1111-1111-1111-111111111111"
```

