from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.money import usage_qty
from app.models import Customer, Metric, UsageAggregate, UsageEvent, utcnow
from app.schemas import UsageEventIn
from app.services import audit, outbox


def _month_bounds(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    if start.month == 12:
        end = date(start.year + 1, 1, 1)
    else:
        end = date(start.year, start.month + 1, 1)
    # period_end is exclusive in aggregates; store inclusive last day for invoice UX
    from datetime import timedelta

    return start, end - timedelta(days=1)


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


def ingest_event(
    db: Session,
    *,
    organization_id: str,
    event: UsageEventIn,
    actor_user_id: str | None = None,
) -> tuple[UsageEvent, bool]:
    """Insert usage event idempotently. Returns (row, duplicate)."""
    customer = resolve_customer(db, organization_id, event.customer_external_ref)
    metric = resolve_metric(db, organization_id, event.metric_code)
    qty = usage_qty(event.quantity)

    existing = db.scalar(
        select(UsageEvent).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.event_id == event.event_id,
        )
    )
    if existing is not None:
        return existing, True

    row = UsageEvent(
        organization_id=organization_id,
        customer_id=customer.id,
        metric_id=metric.id,
        event_id=event.event_id,
        quantity=qty,
        occurred_at=event.occurred_at,
        properties_json=json.dumps(event.properties) if event.properties else None,
        status="applied",
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(UsageEvent).where(
                UsageEvent.organization_id == organization_id,
                UsageEvent.event_id == event.event_id,
            )
        )
        if existing is None:
            raise
        return existing, True

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
            "occurred_at": event.occurred_at.isoformat(),
        },
    )
    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="usage.ingest",
        entity_type="usage_event",
        entity_id=row.id,
        details={"event_id": event.event_id, "quantity": str(qty)},
    )
    outbox.maybe_process_sync(db)
    return row, False


def apply_aggregate_from_event(db: Session, payload: dict) -> None:
    qty = usage_qty(payload["quantity"])
    occurred = date.fromisoformat(payload["occurred_at"][:10])
    period_start, period_end = _month_bounds(occurred)
    org_id = payload["organization_id"]
    customer_id = payload["customer_id"]
    metric_id = payload["metric_id"]

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
    agg.quantity = usage_qty(agg.quantity + qty)
    agg.updated_at = utcnow()


def sum_usage(
    db: Session,
    *,
    organization_id: str,
    customer_id: str,
    metric_id: str,
    period_start: date,
    period_end: date,
) -> Decimal:
    """Sum events whose occurred_at date falls in [period_start, period_end] inclusive."""
    rows = db.scalars(
        select(UsageEvent).where(
            UsageEvent.organization_id == organization_id,
            UsageEvent.customer_id == customer_id,
            UsageEvent.metric_id == metric_id,
            UsageEvent.status == "applied",
        )
    ).all()
    total = Decimal("0")
    for row in rows:
        d = row.occurred_at.date() if hasattr(row.occurred_at, "date") else row.occurred_at
        if period_start <= d <= period_end:
            total = usage_qty(total + usage_qty(row.quantity))
    return total
