from __future__ import annotations

import argparse
import os
from uuid import UUID

from app.fact_repository import PostgresOperationalFactRepository
from app.fact_service import OperationalFactDerivationService, OperationalFactRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Derive deterministic operational facts from normalized events.")
    parser.add_argument("--tenant-id", type=UUID, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/telemetry_app")
    repository = PostgresOperationalFactRepository(database_url=database_url)
    service = OperationalFactDerivationService(repository=repository)
    result = service.run(OperationalFactRequest(tenant_id=args.tenant_id))
    print(
        f"operational_fact_run_id={result.run_id} "
        f"session_slice_count={result.session_slice_count} "
        f"idle_window_count={result.idle_window_count} "
        f"application_usage_count={result.application_usage_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

