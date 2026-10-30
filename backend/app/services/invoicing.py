from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.money import money, sum_money
from app.models import (
    Customer,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Metric,
    ShadowInvoice,
    Subscription,
)
from app.services import audit
from app.services.metering import sum_usage
from app.services.pricing import get_version, price_quantity


def _next_invoice_number(db: Session, organization_id: str) -> str:
    count = db.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.organization_id == organization_id)
    )
    return f"INV-{(count or 0) + 1:06d}"


def generate_invoice(
    db: Session,
    *,
    organization_id: str,
    customer_id: str,
    period_start: date,
    period_end: date,
    subscription_id: str | None = None,
    finalize: bool = True,
    actor_user_id: str | None = None,
) -> Invoice:
    customer = db.get(Customer, customer_id)
    if customer is None or customer.organization_id != organization_id:
        raise ValueError("customer not found")

    subscription: Subscription | None = None
    if subscription_id:
        subscription = db.get(Subscription, subscription_id)
        if subscription is None or subscription.organization_id != organization_id:
            raise ValueError("subscription not found")
    else:
        subscription = db.scalar(
            select(Subscription).where(
                Subscription.organization_id == organization_id,
                Subscription.customer_id == customer_id,
                Subscription.status == "active",
            )
        )
        if subscription is None:
            raise ValueError("no active subscription for customer")

    version = get_version(db, subscription.pricing_version_id)
    invoice = Invoice(
        organization_id=organization_id,
        customer_id=customer_id,
        subscription_id=subscription.id,
        pricing_version_id=version.id,
        number=_next_invoice_number(db, organization_id),
        status=InvoiceStatus.open if finalize else InvoiceStatus.draft,
        currency=customer.currency,
        period_start=period_start,
        period_end=period_end,
    )
    db.add(invoice)
    db.flush()

    lines: list[InvoiceLine] = []
    amounts: list[Decimal] = []

    base = money(version.base_fee)
    if base:
        line = InvoiceLine(
            invoice_id=invoice.id,
            description="Base subscription fee",
            quantity=Decimal("1"),
            unit_price=base,
            amount=base,
        )
        db.add(line)
        lines.append(line)
        amounts.append(base)

    for component in version.components:
        qty = sum_usage(
            db,
            organization_id=organization_id,
            customer_id=customer_id,
            metric_id=component.metric_id,
            period_start=period_start,
            period_end=period_end,
        )
        unit, amount = price_quantity(component, qty)
        metric = db.get(Metric, component.metric_id)
        desc = f"Usage: {metric.code if metric else component.metric_id}"
        line = InvoiceLine(
            invoice_id=invoice.id,
            metric_id=component.metric_id,
            description=desc,
            quantity=qty,
            unit_price=unit,
            amount=amount,
        )
        db.add(line)
        lines.append(line)
        amounts.append(amount)

    invoice.subtotal = sum_money(amounts)
    invoice.total = invoice.subtotal
    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="invoice.generate",
        entity_type="invoice",
        entity_id=invoice.id,
        details={"number": invoice.number, "total": str(invoice.total)},
    )
    return invoice


def shadow_compare(
    db: Session,
    *,
    organization_id: str,
    invoice_id: str,
    alternate_pricing_version_id: str,
    actor_user_id: str | None = None,
) -> ShadowInvoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.organization_id != organization_id:
        raise ValueError("invoice not found")
    alt = get_version(db, alternate_pricing_version_id)
    amounts: list[Decimal] = []
    base = money(alt.base_fee)
    if base:
        amounts.append(base)
    for component in alt.components:
        qty = sum_usage(
            db,
            organization_id=organization_id,
            customer_id=invoice.customer_id,
            metric_id=component.metric_id,
            period_start=invoice.period_start,
            period_end=invoice.period_end,
        )
        _, amount = price_quantity(component, qty)
        amounts.append(amount)
    total = sum_money(amounts)
    delta = money(total - money(invoice.total))
    shadow = ShadowInvoice(
        organization_id=organization_id,
        customer_id=invoice.customer_id,
        source_invoice_id=invoice.id,
        pricing_version_id=alt.id,
        total=total,
        delta=delta,
    )
    db.add(shadow)
    db.flush()
    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="invoice.shadow_compare",
        entity_type="shadow_invoice",
        entity_id=shadow.id,
        details={"source": invoice.id, "delta": str(delta)},
    )
    return shadow
