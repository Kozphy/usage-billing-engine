from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import WebhookEvent
from app.services import audit
from app.services.payments import mark_paid_from_webhook, verify_stripe_signature


def ingest_webhook(
    db: Session,
    *,
    organization_id: str,
    provider: str,
    provider_event_id: str,
    event_type: str,
    payload: dict,
    raw_body: bytes | None = None,
    signature_header: str | None = None,
    webhook_secret: str | None = None,
) -> tuple[WebhookEvent, bool]:
    if provider == "stripe":
        if not signature_header or not webhook_secret or raw_body is None:
            raise PermissionError("stripe webhook signature required")
        if not verify_stripe_signature(raw_body, signature_header, webhook_secret):
            raise PermissionError("invalid webhook signature")

    existing = db.scalar(
        select(WebhookEvent).where(
            WebhookEvent.organization_id == organization_id,
            WebhookEvent.provider == provider,
            WebhookEvent.provider_event_id == provider_event_id,
        )
    )
    if existing is not None:
        return existing, True

    row = WebhookEvent(
        organization_id=organization_id,
        provider=provider,
        provider_event_id=provider_event_id,
        event_type=event_type,
        payload_json=json.dumps(payload),
        processed=False,
    )
    db.add(row)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        existing = db.scalar(
            select(WebhookEvent).where(
                WebhookEvent.organization_id == organization_id,
                WebhookEvent.provider == provider,
                WebhookEvent.provider_event_id == provider_event_id,
            )
        )
        if existing is None:
            raise
        return existing, True

    if event_type in {"invoice.paid", "payment_intent.succeeded", "charge.succeeded"}:
        provider_payment_id = (
            payload.get("provider_payment_id")
            or payload.get("id")
            or payload.get("data", {}).get("object", {}).get("id")
        )
        if provider_payment_id:
            mark_paid_from_webhook(
                db,
                organization_id=organization_id,
                provider_payment_id=str(provider_payment_id),
                payload=payload,
            )
    row.processed = True
    audit.write_audit(
        db,
        organization_id=organization_id,
        action="webhook.ingest",
        entity_type="webhook_event",
        entity_id=row.id,
        details={"event_type": event_type, "provider": provider},
    )
    return row, False
