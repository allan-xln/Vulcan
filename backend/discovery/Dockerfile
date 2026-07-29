FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY backend/discovery/pyproject.toml ./pyproject.toml
COPY backend/discovery/app ./app

RUN python -m pip wheel --wheel-dir /wheels .

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10002 vulcan-discovery \
    && useradd --uid 10002 --gid 10002 --no-create-home --shell /usr/sbin/nologin vulcan-discovery

COPY --from=builder /wheels /wheels
RUN python -m pip install /wheels/* \
    && rm -rf /wheels

WORKDIR /app
USER vulcan-discovery

CMD ["python", "-m", "app.main"]
