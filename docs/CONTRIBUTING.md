# Contributing

## Principles

- Preserve tenant isolation.
- Do not add surveillance behavior.
- Keep AI grounded in structured facts.
- Prefer small, testable changes.
- Do not commit generated artifacts, caches, virtual environments, or local secrets.

## Validation

Run focused tests before opening changes:

```bash
pnpm --dir frontend/web test:unit
.venv/bin/python -m pytest ai/api/tests
.venv/bin/python -m pytest backend/ingestion-gateway/tests
.venv/bin/python -m pytest backend/jobs/tests
.venv/bin/python -m pytest backend/query-api/tests
```

## Naming

Use Vulcan product language:

- operational events
- operational facts
- operational intelligence
- insights
- recommendations
- automation opportunities

Avoid positioning the product as monitoring, surveillance, espionage, or employee control.

