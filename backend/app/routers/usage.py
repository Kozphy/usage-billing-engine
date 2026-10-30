from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import UsageBatchIn, UsageEventIn, UsageEventOut
from app.security import get_current_user
from app.services import metering

router = APIRouter(prefix="/usage", tags=["usage"])


@router.post("/events", response_model=UsageEventOut)
def ingest_one(
    body: UsageEventIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> UsageEventOut:
    try:
        row, duplicate = metering.ingest_event(
            db,
            organization_id=user.organization_id,
            event=body,
            actor_user_id=user.id,
        )
        db.commit()
        return UsageEventOut(id=row.id, event_id=row.event_id, status=row.status, duplicate=duplicate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/events:batch", response_model=list[UsageEventOut])
def ingest_batch(
    body: UsageBatchIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[UsageEventOut]:
    results: list[UsageEventOut] = []
    try:
        for event in body.events:
            row, duplicate = metering.ingest_event(
                db,
                organization_id=user.organization_id,
                event=event,
                actor_user_id=user.id,
            )
            results.append(
                UsageEventOut(
                    id=row.id,
                    event_id=row.event_id,
                    status=row.status,
                    duplicate=duplicate,
                )
            )
        db.commit()
        return results
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
