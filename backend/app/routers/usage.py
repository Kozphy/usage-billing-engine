"""Usage event ingest routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import EventConflictError
from app.logging_setup import correlation_id_var
from app.models import User
from app.schemas import UsageBatchIn, UsageEventIn, UsageEventOut
from app.security import get_current_user
from app.services import metering

router = APIRouter(prefix="/usage", tags=["usage"])


def _out(row, *, duplicate: bool, conflict: bool = False) -> UsageEventOut:
    """Map a usage event ORM row to the API response schema.

    Args:
        row: Persisted ``UsageEvent``.
        duplicate: Whether this request was an idempotent replay.
        conflict: Reserved flag for conflict responses (usually False here).

    Returns:
        ``UsageEventOut`` response model.
    """
    return UsageEventOut(
        id=row.id,
        event_id=row.event_id,
        status=row.status,
        duplicate=duplicate,
        conflict=conflict,
        received_at=row.received_at,
        correlation_id=row.correlation_id,
        schema_version=row.schema_version,
    )


@router.post("/events", response_model=UsageEventOut)
def ingest_one(
    body: UsageEventIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> UsageEventOut:
    """Ingest a single usage event with persist-before-ack semantics.

    Args:
        body: Usage event payload.
        request: Incoming request (correlation header).
        db: Database session.
        user: Authenticated tenant user.

    Returns:
        Accepted or duplicate event response.

    Raises:
        HTTPException: 409 on content conflict, 400 on validation/domain errors.
    """
    cid = request.headers.get("x-correlation-id") or correlation_id_var.get()
    try:
        row, duplicate = metering.ingest_event(
            db,
            organization_id=user.organization_id,
            event=body,
            actor_user_id=user.id,
            correlation_id=cid,
        )
        db.commit()
        return _out(row, duplicate=duplicate)
    except EventConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/events:batch", response_model=list[UsageEventOut])
def ingest_batch(
    body: UsageBatchIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[UsageEventOut]:
    """Ingest a batch of usage events in one transaction.

    Args:
        body: Batch payload of usage events.
        request: Incoming request (correlation header).
        db: Database session.
        user: Authenticated tenant user.

    Returns:
        Per-event accept/duplicate responses.

    Raises:
        HTTPException: 409 on content conflict, 400 on validation/domain errors.
    """
    cid = request.headers.get("x-correlation-id") or correlation_id_var.get()
    results: list[UsageEventOut] = []
    try:
        for event in body.events:
            row, duplicate = metering.ingest_event(
                db,
                organization_id=user.organization_id,
                event=event,
                actor_user_id=user.id,
                correlation_id=cid,
            )
            results.append(_out(row, duplicate=duplicate))
        db.commit()
        return results
    except EventConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
