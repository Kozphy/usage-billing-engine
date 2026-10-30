from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import OutboxMessage, OutboxStatus, utcnow


def enqueue(
    db: Session,
    *,
    organization_id: str,
    topic: str,
    payload: dict[str, Any],
) -> OutboxMessage:
    msg = OutboxMessage(
        organization_id=organization_id,
        topic=topic,
        payload_json=json.dumps(payload),
        status=OutboxStatus.pending,
    )
    db.add(msg)
    db.flush()
    return msg


def process_pending(db: Session, limit: int = 100) -> int:
    """Drain pending outbox rows. Aggregation handlers run inline."""
    from app.services.metering import apply_aggregate_from_event

    rows = db.scalars(
        select(OutboxMessage)
        .where(OutboxMessage.status == OutboxStatus.pending)
        .order_by(OutboxMessage.created_at)
        .limit(limit)
    ).all()
    processed = 0
    for row in rows:
        row.status = OutboxStatus.processing
        row.attempts += 1
        db.flush()
        try:
            payload = json.loads(row.payload_json)
            if row.topic == "usage.ingested":
                apply_aggregate_from_event(db, payload)
            row.status = OutboxStatus.done
            row.processed_at = utcnow()
            processed += 1
        except Exception as exc:  # noqa: BLE001 — record and continue
            row.status = OutboxStatus.failed
            row.last_error = str(exc)
    return processed


def maybe_process_sync(db: Session) -> None:
    if get_settings().outbox_sync:
        process_pending(db)
