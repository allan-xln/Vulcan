FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY backend/api/pyproject.toml ./pyproject.toml
COPY backend/api/app ./app

RUN python -m pip wheel --wheel-dir /wheels .

FROM python:3.11-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    LOCAL_API_HOST=0.0.0.0 \
    LOCAL_API_PORT=3001

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 vulcan \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin vulcan

COPY --from=builder /wheels /wheels
RUN python -m pip install /wheels/* \
    && rm -rf /wheels

WORKDIR /app

FROM runtime-base AS migration

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash postgresql-client \
    && rm -rf /var/lib/apt/lists/*
COPY database /app/database
COPY scripts/apply-supabase-migrations.sh /app/scripts/apply-supabase-migrations.sh
COPY scripts/provision-production-access.py /app/scripts/provision-production-access.py
USER vulcan

FROM runtime-base AS runtime

USER vulcan
EXPOSE 3001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001", "--proxy-headers", "--forwarded-allow-ips=*"]
