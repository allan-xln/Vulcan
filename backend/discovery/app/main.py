from __future__ import annotations

import asyncio
import json
import signal
from datetime import datetime, timezone
from pathlib import Path

from app.config import DiscoverySettings, get_settings
from app.repository import DiscoveryRepository
from app.scanner import scan_policy


class DiscoveryWorker:
    def __init__(self, settings: DiscoverySettings, repository: DiscoveryRepository) -> None:
        self.settings = settings
        self.repository = repository
        self.running = True

    def stop(self, *_args: object) -> None:
        self.running = False

    def _write_health(self, status: str, detail: str, run_id: str | None = None) -> None:
        payload = {
            "status": status,
            "detail": detail,
            "enabled": self.settings.enabled,
            "readOnly": True,
            "runId": run_id,
            "checkedAt": datetime.now(timezone.utc).isoformat(),
        }
        path = Path(self.settings.health_file)
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        print(json.dumps({"service": "vulcan-discovery", **payload}, sort_keys=True), flush=True)

    async def run_once(self) -> bool:
        if not self.settings.enabled:
            self._write_health("disabled", "Discovery está desativado por configuração.")
            return False
        run = self.repository.claim_next_run()
        if run is None:
            self._write_health("ok", "Fila sem execuções pendentes.")
            return False
        try:
            observations = await scan_policy(
                run.policy,
                allow_public_networks=self.settings.allow_public_networks,
                global_max_targets=self.settings.max_targets_per_run,
                global_max_concurrency=self.settings.max_concurrency,
                global_max_timeout_ms=self.settings.max_timeout_ms,
                globally_allowed_tcp_ports=self.settings.allowed_tcp_ports,
            )
            self.repository.complete_run(run, observations)
            self._write_health(
                "ok",
                f"Execução concluída com {len(observations)} alvo(s).",
                str(run.id),
            )
        except Exception as exc:
            self.repository.fail_run(run, str(exc))
            self._write_health("degraded", "Execução falhou de forma isolada.", str(run.id))
        return True

    async def run_forever(self) -> None:
        while self.running:
            await self.run_once()
            await asyncio.sleep(self.settings.worker_poll_seconds)


def main() -> int:
    settings = get_settings()
    repository = DiscoveryRepository(settings.database_url)
    worker = DiscoveryWorker(settings, repository)
    signal.signal(signal.SIGTERM, worker.stop)
    signal.signal(signal.SIGINT, worker.stop)
    asyncio.run(worker.run_forever())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
