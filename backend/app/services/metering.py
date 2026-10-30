from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import EventConflictError
from app.logging_setup import get_logger
from app.money import usage_qty
from app.models import (
    Customer,
    Invoice,
    InvoiceAdjustment,
    InvoiceStatus,
    Metric,
    UsageAggregate,
    UsageEvent,
    new_id,
    utcnow,
)
from app.schemas import UsageEventIn
from app.services import audit, outbox

log = get_logger(__name__)

# Late / out-of-order policy (documented in docs/financial-invariants.md):
# - Billing periods are UTC calendar months by default; invoice period is inclusive
#   on both period_start and period_end dates.
# - Events are accepted if identifiers/quantities/timestamps validate, regardless of
#   arrival order. Aggregates use occurred_at (event time), not received_at.
# - If a finalized/open invoice already exists for the event's period, the event is
#   persisted with status=late and an InvoiceAdjustment is created. The finalized
#   invoice totals are never rewritten.


def _month_bounds(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    if start.month == 12:
        end = date(start.year + 1, 1, 1)
    else:
        end = date(start.year, start.month + 1, 1)
    return start, end - timedelta(days=1)


def content_hash(
    *,
    customer_id: str,
    metric_id: str,
    quantity: Decimal,
    occurred_at: datetime,
    schema_version: int,
) -> str:
    occurred = occurred_at.astimezone(timezone.utc).isoformat()
    raw = f"{customer_id}|{metric_id}|{quantity}|{occurred}|{schema_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def resolve_customer(db: Session, organization_id: str, external_ref: str) -> Customer:
    customer = db.scalar(
        select(Customer).where(
            Customer.organization_id == organization_id,
            Customer.external_ref == external_ref,
        )
    )
    if customer is None:
        raise ValueError(f"unknown customer external_ref={external_ref}")
    return customer


def resolve_metric(db: Session, organization_id: str, code: str) -> Metric:
    metric = db.scalar(
        select(Metric).where(Metric.organization_id == organization_id, Metric.code == code)
    )
    if metric is None:
        raise ValueError(f"unknown metric code={code}")
    return metric


def _find_covering_invoice(
    db: Session,
    *,
    organization_id: str,
    customer_id: str,
    occurred: date,
) -> Invoice | None:
    rows = db.scalars(
        select(Invoice).where(
            Invoice.organization_id == organization_id,
            Invoice.customer_id == customer_id,
            Invoice.status.in_(
                [
                    InvoiceStatus.open,
                    InvoiceStatus.paid,
                    InvoiceStatus.finalized,
                ]
            ),
        )
    ).all()
    for inv in rows:
        if inv.finalized_at is None and inv.status == InvoiceStatus.open:
            # Treat open invoices from generate(finalize=True) as finalized snapshots.
            pass
        if inv.period_start <= occurred <= inv.period_end:
            if inv.finalized_at is not None or inv.status in {
                InvoiceStatus.open,
                InvoiceStatus.paid,
                InvoiceStatus.finalized,
            }:
                return inv
    return None


def ingest_event(
    db: Session,
    *,
    organization_id: str,
    event: UsageEventIn,
    actor_user_id: str | None = None,
    correlation_id: str | None = None,
) -> tuple[UsageEvent, bool]:
    """Persist usage before ack.

    Delivery semantics:
    - At-least-once from the client is safe for identical payloads (idempotent).
    - Same event_id with different billable content → EventConflictError (409).
    - This is *not* end-to-end exactly-once; downstream processing is at-least-once
      with idempotent aggregate application keyed by event identity.
    """
    customer = resolve_customer(db, organization_id, event.customer_external_ref)
    metric = resolve_metric(db, organization_id, event.metric_code)
    qty = usage_qty(event.quantity)
    if qty == 0:
        raise ValueError("usage quantity must be > 0")

    digest = content_hash(
        customer_id=customer.id,
        metric_id=metric.id,
        quantity=qty,
        occurred_at=event.occurred_at,
        schema_version=event.schema_version,
    )
    cid = correlation_id or new_id()
    received = utcnow()

    existing = db.scalar(
        select(UsageEvent).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.event_id == event.event_id,
        )
    )
    if existing is not None:
        if existing.content_hash and existing.content_hash != digest:
            raise EventConflictError(
                event.event_id,
                detail=(
                    f"event_id={event.event_id} already stored with different content "
                    f"(stored_hash={existing.content_hash[:12]}… "
                    f"incoming_hash={digest[:12]}…)"
                ),
            )
        return existing, True

    occurred_date = event_occurred_date(event.occurred_at)
    covering = _find_covering_invoice(
        db,
        organization_id=organization_id,
        customer_id=customer.id,
        occurred=occurred_date,
    )
    status = "late" if covering is not None else "pending"

    row = UsageEvent(
        organization_id=organization_id,
        customer_id=customer.id,
        metric_id=metric.id,
        event_id=event.event_id,
        quantity=qty,
        occurred_at=event.occurred_at.astimezone(timezone.utc),
        received_at=received,
        schema_version=event.schema_version,
        content_hash=digest,
        correlation_id=cid,
        properties_json=json.dumps(event.properties) if event.properties else None,
        status=status,
    )
    db.add(row)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        existing = db.scalar(
            select(UsageEvent).where(
                UsageEvent.organization_id == organization_id,
                UsageEvent.event_id == event.event_id,
            )
        )
        if existing is None:
            raise
        if existing.content_hash != digest:
            raise EventConflictError(event.event_id) from None
        return existing, True

    if covering is not None:
        _create_late_adjustment(
            db,
            organization_id=organization_id,
            invoice=covering,
            usage_event=row,
            actor_user_id=actor_user_id,
        )
    else:
        outbox.enqueue(
            db,
            organization_id=organization_id,
            topic="usage.ingested",
            payload={
                "usage_event_id": row.id,
                "organization_id": organization_id,
                "customer_id": customer.id,
                "metric_id": metric.id,
                "quantity": str(qty),
                "occurred_at": row.occurred_at.isoformat(),
                "correlation_id": cid,
            },
            correlation_id=cid,
        )

    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="usage.ingest",
        entity_type="usage_event",
        entity_id=row.id,
        details={
            "event_id": event.event_id,
            "quantity": str(qty),
            "status": status,
            "correlation_id": cid,
        },
    )
    log.info(
        "usage_ingested",
        extra={
            "event_id": event.event_id,
            "organization_id": organization_id,
            "customer_id": customer.id,
            "correlation_id": cid,
        },
    )
    outbox.maybe_process_sync(db)
    return row, False


def _create_late_adjustment(
    db: Session,
    *,
    organization_id: str,
    invoice: Invoice,
    usage_event: UsageEvent,
    actor_user_id: str | None,
) -> InvoiceAdjustment:
    from app.services.pricing import get_version, price_quantity

    version = get_version(db, invoice.pricing_version_id)
    amount = Decimal("0")
    for component in version.components:
        if component.metric_id == usage_event.metric_id:
            _, amount = price_quantity(component, usage_event.quantity)
            break
    adj = InvoiceAdjustment(
        organization_id=organization_id,
        invoice_id=invoice.id,
        usage_event_id=usage_event.id,
        amount=amount,
        reason="late_usage_after_finalization",
        correlation_id=usage_event.correlation_id,
    )
    db.add(adj)
    db.flush()
    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="invoice.adjustment_late_usage",
        entity_type="invoice_adjustment",
        entity_id=adj.id,
        details={
            "invoice_id": invoice.id,
            "usage_event_id": usage_event.id,
            "amount": str(amount),
        },
    )
    return adj


def apply_aggregate_from_event(db: Session, payload: dict) -> None:
    """Idempotent aggregate bump: replaying the same usage_event_id does not double-count.

    Aggregate quantity is recomputed from applied events for the period rather than
    blindly adding, so at-least-once outbox delivery is safe.
    """
    usage_event_id = payload["usage_event_id"]
    event = db.get(UsageEvent, usage_event_id)
    if event is None:
        raise ValueError(f"usage event missing: {usage_event_id}")

    occurred = event_occurred_date(event.occurred_at)
    period_start, period_end = _month_bounds(occurred)
    org_id = event.organization_id
    customer_id = event.customer_id
    metric_id = event.metric_id

    # Mark applied before recompute so sum_usage includes this row.
    if event.status == "pending":
        event.status = "applied"

    total = sum_usage(
        db,
        organization_id=org_id,
        customer_id=customer_id,
        metric_id=metric_id,
        period_start=period_start,
        period_end=period_end,
    )

    agg = db.scalar(
        select(UsageAggregate).where(
            UsageAggregate.organization_id == org_id,
            UsageAggregate.customer_id == customer_id,
            UsageAggregate.metric_id == metric_id,
            UsageAggregate.period_start == period_start,
            UsageAggregate.period_end == period_end,
        )
    )
    if agg is None:
        agg = UsageAggregate(
            organization_id=org_id,
            customer_id=customer_id,
            metric_id=metric_id,
            period_start=period_start,
            period_end=period_end,
            quantity=Decimal("0"),
        )
        db.add(agg)
        db.flush()
    agg.quantity = total
    agg.updated_at = utcnow()


def event_occurred_date(occurred_at: datetime) -> date:
    """Normalize to UTC calendar date. Naive timestamps are treated as UTC (not local)."""
    if occurred_at.tzinfo is None:
        return occurred_at.replace(tzinfo=timezone.utc).date()
    return occurred_at.astimezone(timezone.utc).date()


def sum_usage(
    db: Session,
    *,
    organization_id: str,
    customer_id: str,
    metric_id: str,
    period_start: date,
    period_end: date,
) -> Decimal:
    """Sum events whose occurred_at date falls in [period_start, period_end] inclusive.

    Includes applied and pending (not yet drained) for invoice generation so billing
    does not depend on outbox lag. Excludes late (already billed via adjustment) and
    discarded.
    """
    rows = db.scalars(
        select(UsageEvent).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.customer_id == customer_id,
            UsageEvent.metric_id == metric_id,
            UsageEvent.status.in_(["applied", "pending"]),
        )
    ).all()
    total = Decimal("0")
    for row in rows:
        d = event_occurred_date(row.occurred_at)
        if period_start <= d <= period_end:
            total = usage_qty(total + usage_qty(row.quantity))
    return total


def list_event_ids_for_period(
    db: Session,
    *,
    organization_id: str,
    customer_id: str,
    metric_id: str,
    period_start: date,
    period_end: date,
) -> list[str]:
    rows = db.scalars(
        select(UsageEvent).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.customer_id == customer_id,
            UsageEvent.metric_id == metric_id,
            UsageEvent.status.in_(["applied", "pending"]),
        )
    ).all()
    ids: list[str] = []
    for row in rows:
        d = event_occurred_date(row.occurred_at)
        if period_start <= d <= period_end:
            ids.append(row.id)
    return ids
