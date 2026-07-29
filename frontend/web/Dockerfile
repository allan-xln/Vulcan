FROM node:22-bookworm-slim AS deps

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY shared/domain/package.json ./shared/domain/package.json
COPY shared/operational-event-schema/package.json ./shared/operational-event-schema/package.json
COPY frontend/web/package.json ./frontend/web/package.json

RUN corepack pnpm install --frozen-lockfile

FROM deps AS build

ARG NEXT_PUBLIC_API_URL=http://localhost:3001
ARG NEXT_PUBLIC_ENVIRONMENT=local
ARG NEXT_PUBLIC_LOCAL_TEST_AUTH=false
ARG NEXT_PUBLIC_MOCK_AUTH=false
ARG NEXT_PUBLIC_DEMO_TENANT_ID=00000000-0000-0000-0000-000000000301
ARG NEXT_PUBLIC_DEMO_ADMIN_EMAIL=admin@vulcan.local
ARG NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY=replace-me
ARG NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=replace-me

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_ENVIRONMENT=${NEXT_PUBLIC_ENVIRONMENT} \
    NEXT_PUBLIC_LOCAL_TEST_AUTH=${NEXT_PUBLIC_LOCAL_TEST_AUTH} \
    NEXT_PUBLIC_MOCK_AUTH=${NEXT_PUBLIC_MOCK_AUTH} \
    NEXT_PUBLIC_DEMO_TENANT_ID=${NEXT_PUBLIC_DEMO_TENANT_ID} \
    NEXT_PUBLIC_DEMO_ADMIN_EMAIL=${NEXT_PUBLIC_DEMO_ADMIN_EMAIL} \
    NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL} \
    NEXT_PUBLIC_SUPABASE_ANON_KEY=${NEXT_PUBLIC_SUPABASE_ANON_KEY} \
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=${NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY}

COPY shared ./shared
COPY frontend/web ./frontend/web

RUN corepack pnpm --dir frontend/web build

FROM node:22-bookworm-slim AS runtime

ENV NODE_ENV=production \
    FRONTEND_PORT=3002 \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3002 \
    HOSTNAME=0.0.0.0
WORKDIR /app

COPY --from=build --chown=node:node /app/frontend/web/.next/standalone ./
COPY --from=build --chown=node:node /app/frontend/web/.next/static ./frontend/web/.next/static
COPY --from=build --chown=node:node /app/frontend/web/public ./frontend/web/public

USER node
EXPOSE 3002

CMD ["node", "frontend/web/server.js"]
