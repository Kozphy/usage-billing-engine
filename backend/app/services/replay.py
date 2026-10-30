from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OutboxMessage, OutboxStatus, UsageEvent
from app.services.outbox import process_pending


def requeue_failed_outbox(db: Session, organization_id: str) -> int:
    rows = db.scalars(
        select(OutboxMessage).where(
            OutboxMessage.organization_id == organization_id,
            OutboxMessage.status == OutboxStatus.failed,
        )
    ).all()
    for row in rows:
        row.status = OutboxStatus.pending
        row.last_error = None
    db.flush()
    return process_pending(db)


def rebuild_aggregates_note(db: Session, organization_id: str) -> dict:
    """Report how many applied events exist for a full rebuild (ops hint)."""
    count = len(
        db.scalars(
            select(UsageEvent).where(
                UsageEvent.organization_id == organization_id,
                UsageEvent.status == "applied",
            )
        ).all()
    )
    return {
        "applied_events": count,
        "hint": "Re-enqueue usage.ingested outbox messages or re-ingest with new event ids for rebuild demos",
    }
