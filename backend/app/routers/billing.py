"""Billing routes: invoices, payments, webhooks, shadow cutover, and ops."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.errors import CutoverBlockedError
from app.models import Invoice, User
from app.schemas import (
    ChargeIn,
    CutoverIn,
    InvoiceAdjustmentOut,
    InvoiceGenerateIn,
    InvoiceLineOut,
    InvoiceOut,
    RefundIn,
    ReportSummaryOut,
    ShadowCompareIn,
)
from app.security import get_current_user
from app.services import invoicing, payments, reporting, replay, webhooks
from app.services.outbox import process_pending, recover_stale_processing

router = APIRouter(tags=["billing"])


def _invoice_out(invoice: Invoice) -> InvoiceOut:
    """Map an invoice ORM graph to the API response schema.

    Args:
        invoice: Invoice with lines/adjustments loaded or lazy-loadable.

    Returns:
        ``InvoiceOut`` response model.
    """
    adjustments = [
        InvoiceAdjustmentOut(
            id=adj.id,
            usage_event_id=adj.usage_event_id,
            amount=adj.amount,
            reason=adj.reason,
            correlation_id=adj.correlation_id,
        )
        for adj in (invoice.adjustments or [])
    ]
    lines = []
    for line in invoice.lines:
        source_ids = None
        if line.source_event_ids_json:
            source_ids = json.loads(line.source_event_ids_json)
        lines.append(
            InvoiceLineOut(
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                amount=line.amount,
                pricing_version_id=line.pricing_version_id,
                source_event_ids=source_ids,
            )
        )
    return InvoiceOut(
        id=invoice.id,
        number=invoice.number,
        status=invoice.status.value if hasattr(invoice.status, "value") else str(invoice.status),
        currency=invoice.currency,
        period_start=invoice.period_start,
        period_end=invoice.period_end,
        subtotal=invoice.subtotal,
        tax_total=invoice.tax_total,
        total=invoice.total,
        correlation_id=invoice.correlation_id,
        finalized_at=invoice.finalized_at,
        lines=lines,
        adjustments=adjustments,
    )


@router.post("/invoices/generate", response_model=InvoiceOut)
def generate_invoice(
    body: InvoiceGenerateIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> InvoiceOut:
    """Generate an idempotent invoice for a customer period.

    Args:
        body: Period and customer selection.
        db: Database session.
        user: Authenticated tenant user.

    Returns:
        Generated or existing invoice snapshot.
    """
    try:
        invoice = invoicing.generate_invoice(
            db,
            organization_id=user.organization_id,
            customer_id=body.customer_id,
            period_start=body.period_start,
            period_end=body.period_end,
            subscription_id=body.subscription_id,
            finalize=body.finalize,
            actor_user_id=user.id,
        )
        db.commit()
        db.refresh(invoice)
        return _invoice_out(invoice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[InvoiceOut]:
    rows = db.scalars(
        select(Invoice).where(Invoice.organization_id == user.organization_id)
    ).all()
    return [_invoice_out(row) for row in rows]


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> InvoiceOut:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.organization_id != user.organization_id:
        raise HTTPException(status_code=404, detail="invoice not found")
    return _invoice_out(invoice)


@router.post("/invoices/{invoice_id}/charge")
def charge(
    invoice_id: str,
    body: ChargeIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Charge an open invoice using an idempotency key.

    Args:
        invoice_id: Invoice to charge.
        body: Charge request with ``idempotency_key``.
        db: Database session.
        user: Authenticated tenant user.

    Returns:
        Payment attempt status payload.
    """
    try:
        attempt = payments.charge_invoice(
            db,
            organization_id=user.organization_id,
            invoice_id=invoice_id,
            idempotency_key=body.idempotency_key,
            actor_user_id=user.id,
        )
        db.commit()
        return {
            "id": attempt.id,
            "status": attempt.status,
            "provider": attempt.provider,
            "provider_payment_id": attempt.provider_payment_id,
            "amount": str(attempt.amount),
            "correlation_id": attempt.correlation_id,
            "last_error": attempt.last_error,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/invoices/{invoice_id}/refund")
def refund(
    invoice_id: str,
    body: RefundIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        row = payments.refund_invoice(
            db,
            organization_id=user.organization_id,
            invoice_id=invoice_id,
            amount=body.amount,
            reason=body.reason,
            actor_user_id=user.id,
        )
        db.commit()
        return {
            "id": row.id,
            "amount": str(row.amount),
            "provider_refund_id": row.provider_refund_id,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/invoices/shadow-compare")
def shadow_compare(
    body: ShadowCompareIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        shadow = invoicing.shadow_compare(
            db,
            organization_id=user.organization_id,
            invoice_id=body.invoice_id,
            alternate_pricing_version_id=body.alternate_pricing_version_id,
            expected_delta=body.expected_delta,
            actor_user_id=user.id,
        )
        db.commit()
        return {
            "id": shadow.id,
            "total": str(shadow.total),
            "delta": str(shadow.delta),
            "source_invoice_id": shadow.source_invoice_id,
            "pricing_version_id": shadow.pricing_version_id,
            "classification": shadow.classification,
            "cutover_allowed": shadow.cutover_allowed,
            "notes": shadow.notes,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pricing/cutover")
def cutover(
    body: CutoverIn,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        row = invoicing.execute_cutover(
            db,
            organization_id=user.organization_id,
            plan_code=body.plan_code,
            to_pricing_version_id=body.to_pricing_version_id,
            invoice_ids=body.invoice_ids,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": row.id, "action": row.action, "report": json.loads(row.shadow_report_json or "[]")}
    except CutoverBlockedError as exc:
        db.commit()  # persist blocked cutover audit row
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/pricing/cutover/{cutover_id}/rollback")
def rollback_cutover(
    cutover_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        row = invoicing.rollback_cutover(
            db,
            organization_id=user.organization_id,
            cutover_id=cutover_id,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": row.id, "action": row.action}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/webhooks/{provider}")
async def webhook(
    provider: str,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Provider webhooks. organization_id query param required for multi-tenant demos."""
    organization_id = request.query_params.get("organization_id")
    if not organization_id:
        raise HTTPException(status_code=400, detail="organization_id query param required")
    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="invalid JSON") from exc
    provider_event_id = str(payload.get("id") or payload.get("provider_event_id") or "")
    event_type = str(payload.get("type") or payload.get("event_type") or "unknown")
    if not provider_event_id:
        raise HTTPException(status_code=400, detail="payload missing id")
    settings = get_settings()
    try:
        row, duplicate = webhooks.ingest_webhook(
            db,
            organization_id=organization_id,
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            payload=payload,
            raw_body=raw,
            signature_header=request.headers.get("Stripe-Signature"),
            webhook_secret=settings.stripe_webhook_secret if provider == "stripe" else None,
        )
        db.commit()
        return {"id": row.id, "duplicate": duplicate, "processed": row.processed}
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/reports/summary", response_model=ReportSummaryOut)
def report_summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ReportSummaryOut:
    return reporting.summary(db, user.organization_id)


@router.post("/ops/outbox/process")
def drain_outbox(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    recover_stale_processing(db)
    count = process_pending(db, worker_id=f"api-{user.id[:8]}")
    db.commit()
    return {"processed": count}


@router.post("/ops/outbox/replay-failed")
def replay_failed(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    count = replay.requeue_failed_outbox(db, user.organization_id)
    db.commit()
    return {"reprocessed": count}


@router.get("/ops/rebuild-hint")
def rebuild_hint(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    return replay.rebuild_aggregates_note(db, user.organization_id)
