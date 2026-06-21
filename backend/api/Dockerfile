FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend/api \
    LOCAL_API_HOST=0.0.0.0 \
    LOCAL_API_PORT=3001

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY backend/api /app/backend/api
COPY database /app/database
COPY scripts /app/scripts

RUN pip install --upgrade pip \
    && pip install /app/backend/api

EXPOSE 3001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001", "--app-dir", "/app/backend/api"]
