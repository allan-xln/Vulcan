from __future__ import annotations

import argparse
import json
import logging
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.repository import VulcanRepository
from app.runtime_config import PROJECT_ROOT
from app.whatsapp import WhatsAppConnection


logger = logging.getLogger("vulcan.whatsapp-worker")
running = True
HEALTH_FILE = PROJECT_ROOT / ".runtime" / "whatsapp-worker-health.json"


def stop_worker(signum: int, _frame: object) -> None:
    global running
    running = False
    logger.info(json.dumps({"event": "worker.stop", "signal": signum}))


def write_health(payload: dict) -> None:
    HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = HEALTH_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(HEALTH_FILE)


def run_cycle(repo: VulcanRepository, batch_size: int) -> dict:
    settings = get_settings()
    session = WhatsAppConnection(settings).session()
    items = repo.dispatch_root_whatsapp_queue_system(limit=batch_size)
    counts = repo.root_whatsapp_queue_counts_system()
    payload = {
        "status": "ok",
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "provider": session.provider,
        "providerStatus": session.status,
        "providerConnected": session.connected,
        "processed": len(items),
        "queue": counts,
    }
    write_health(payload)
    logger.info(json.dumps({"event": "worker.cycle", **payload}, ensure_ascii=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Processa a fila WhatsApp raiz do Vulcan.")
    parser.add_argument("--once", action="store_true", help="Executa um ciclo e encerra.")
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)

    settings = get_settings()
    repo = VulcanRepository(settings)
    if not repo.enabled:
        logger.error(json.dumps({"event": "worker.failed", "reason": "DATABASE_URL ausente ou MOCK_DATA ativo"}))
        return 2

    while running:
        try:
            run_cycle(repo, max(1, min(args.batch_size, 100)))
        except Exception as exc:
            logger.exception(json.dumps({"event": "worker.failed", "error": type(exc).__name__}))
            write_health({
                "status": "error",
                "checkedAt": datetime.now(timezone.utc).isoformat(),
                "error": type(exc).__name__,
            })
        if args.once:
            break
        for _ in range(settings.whatsapp_worker_poll_seconds):
            if not running:
                break
            time.sleep(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
