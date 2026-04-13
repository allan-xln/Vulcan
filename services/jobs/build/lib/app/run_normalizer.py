from __future__ import annotations

import argparse
import os
from uuid import UUID

from app.normalization_repository import PostgresNormalizationRepository
from app.normalization_service import NormalizationRequest, TelemetryNormalizationService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize accepted raw telemetry intake into deterministic operational events.")
    parser.add_argument("--tenant-id", type=UUID, default=None)
    parser.add_argument("--batch-limit", type=int, default=500)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/telemetry_app")
    repository = PostgresNormalizationRepository(database_url=database_url)
    service = TelemetryNormalizationService(repository=repository)
    result = service.run(
        NormalizationRequest(
            tenant_id=args.tenant_id,
            batch_limit=args.batch_limit,
        )
    )
    print(
        f"normalization_run_id={result.normalization_run_id} "
        f"processed_count={result.processed_count} "
        f"duplicate_count={result.duplicate_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

