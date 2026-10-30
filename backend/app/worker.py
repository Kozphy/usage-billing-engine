"""Durable outbox worker.

Design choice for this scope: transactional outbox in Postgres + a single
long-running worker process (optionally scaled) claiming rows with
FOR UPDATE SKIP LOCKED. Avoids Kafka/Celery complexity while demonstrating
restart recovery, bounded retries, and concurrent-safe processing.
"""

from __future__ import annotations

import os
import signal
import time
import uuid

from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db import engine
from app.logging_setup import configure_logging, get_logger
from app.services.outbox import process_pending, recover_stale_processing

configure_logging(get_settings().log_level)
log = get_logger("worker")
_running = True


def _stop(*_args: object) -> None:
    global _running
    _running = False


def run(poll_seconds: float = 0.5) -> None:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    get_settings()  # ensure env loaded before engine use
    worker_id = os.environ.get("WORKER_ID") or f"worker-{uuid.uuid4().hex[:8]}"
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    log.info("worker_started", extra={"organization_id": None})
    print(f'{{"message":"worker_started","worker_id":"{worker_id}"}}', flush=True)

    while _running:
        db = Session()
        try:
            recover_stale_processing(db, older_than_seconds=30)
            n = process_pending(db, limit=100, worker_id=worker_id)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            log.error("worker_loop_error", extra={"organization_id": None})
            print(f'{{"message":"worker_loop_error","error":"{exc}"}}', flush=True)
            n = 0
        finally:
            db.close()
        time.sleep(0.05 if n else poll_seconds)


if __name__ == "__main__":
    run()
