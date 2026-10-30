from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_setup import get_logger
from app.models import OutboxMessage, OutboxStatus, utcnow

log = get_logger(__name__)


def enqueue(
    db: Session,
    *,
    organization_id: str,
    topic: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
) -> OutboxMessage:
    settings = get_settings()
    msg = OutboxMessage(
        organization_id=organization_id,
        topic=topic,
        payload_json=json.dumps(payload),
        status=OutboxStatus.pending,
        max_attempts=settings.outbox_max_attempts,
        correlation_id=correlation_id or payload.get("correlation_id"),
        available_at=utcnow(),
    )
    db.add(msg)
    db.flush()
    return msg


def _claim_pending(db: Session, *, limit: int, worker_id: str) -> list[OutboxMessage]:
    """Claim pending rows. Postgres uses SKIP LOCKED; SQLite uses plain select."""
    settings = get_settings()
    now = utcnow()
    stmt = (
        select(OutboxMessage)
        .where(
            OutboxMessage.status == OutboxStatus.pending,
            OutboxMessage.available_at <= now,
        )
        .order_by(OutboxMessage.created_at)
        .limit(limit)
    )
    if settings.is_postgres:
        stmt = stmt.with_for_update(skip_locked=True)
    rows = list(db.scalars(stmt).all())
    for row in rows:
        row.status = OutboxStatus.processing
        row.locked_by = worker_id
        row.attempts += 1
    db.flush()
    return rows


def process_pending(db: Session, limit: int = 100, worker_id: str | None = None) -> int:
    """Drain claimed outbox rows. Safe under concurrent workers (SKIP LOCKED on Postgres)."""
    from app.services.metering import apply_aggregate_from_event

    settings = get_settings()
    wid = worker_id or settings.worker_id
    rows = _claim_pending(db, limit=limit, worker_id=wid)
    processed = 0
    for row in rows:
        try:
            payload = json.loads(row.payload_json)
            if row.topic == "usage.ingested":
                apply_aggregate_from_event(db, payload)
            elif row.topic == "usage.force_fail":
                raise RuntimeError(payload.get("error", "forced outbox failure"))
            else:
                raise ValueError(f"unknown outbox topic: {row.topic}")
            row.status = OutboxStatus.done
            row.processed_at = utcnow()
            row.last_error = None
            row.locked_by = None
            processed += 1
            log.info(
                "outbox_done",
                extra={"outbox_id": row.id, "organization_id": row.organization_id},
            )
        except Exception as exc:  # noqa: BLE001 — record and continue
            row.last_error = str(exc)
            row.locked_by = None
            if row.attempts >= row.max_attempts:
                row.status = OutboxStatus.failed
                log.error(
                    "outbox_terminal_failure",
                    extra={"outbox_id": row.id, "organization_id": row.organization_id},
                )
            else:
                row.status = OutboxStatus.pending
                backoff = settings.outbox_backoff_seconds * row.attempts
                row.available_at = utcnow() + timedelta(seconds=backoff)
                log.warning(
                    "outbox_retry_scheduled",
                    extra={"outbox_id": row.id, "organization_id": row.organization_id},
                )
    return processed


def recover_stale_processing(db: Session, older_than_seconds: int = 60) -> int:
    """Worker crash recovery: return processing rows to pending."""
    cutoff = utcnow() - timedelta(seconds=older_than_seconds)
    rows = db.scalars(
        select(OutboxMessage).where(OutboxMessage.status == OutboxStatus.processing)
    ).all()
    reclaimed = 0
    for row in rows:
        # Reclaim if lock is older than threshold, or threshold is zero (test/force).
        if older_than_seconds == 0 or row.available_at <= cutoff or row.created_at <= cutoff:
            row.status = OutboxStatus.pending
            row.locked_by = None
            row.available_at = utcnow()
            reclaimed += 1
    db.flush()
    return reclaimed


def maybe_process_sync(db: Session) -> None:
    if get_settings().outbox_sync:
        process_pending(db)
