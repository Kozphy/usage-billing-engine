"""Append-only audit log writes."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit(
    db: Session,
    *,
    organization_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_user_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Persist an audit log row for a domain action.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant that owns the action.
        action: Stable action name (for example ``usage.ingest``).
        entity_type: Entity kind string (for example ``invoice``).
        entity_id: Primary key of the affected entity.
        actor_user_id: Optional authenticated user id.
        details: Optional JSON-serializable context.

    Returns:
        Newly added ``AuditLog`` instance (not yet committed).
    """
    row = AuditLog(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=json.dumps(details) if details is not None else None,
    )
    db.add(row)
    return row
