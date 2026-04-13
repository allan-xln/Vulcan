from __future__ import annotations

import argparse
import os
from datetime import date
from uuid import UUID

from app.daily_metrics_repository import PostgresDailyMetricRepository
from app.daily_metrics_service import DailyMetricDerivationService, DailyMetricRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive deterministic daily operational metrics.")
    parser.add_argument("--tenant-id", type=UUID, default=None)
    parser.add_argument("--metric-date", type=date.fromisoformat, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/telemetry_app")
    repository = PostgresDailyMetricRepository(database_url=database_url)
    service = DailyMetricDerivationService(repository=repository)
    result = service.run(DailyMetricRequest(tenant_id=args.tenant_id, metric_date=args.metric_date))
    print(f"daily_metric_run_id={result.run_id} metric_row_count={result.metric_row_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

