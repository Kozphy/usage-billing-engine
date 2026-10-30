"""Invoice generation, immutability, shadow compare, and pricing cutover."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import CutoverBlockedError, InvoiceImmutableError
from app.money import money, sum_money
from app.models import (
    Customer,
    Invoice,
    InvoiceAdjustment,
    InvoiceLine,
    InvoiceStatus,
    Metric,
    PricingCutover,
    PricingPlan,
    ShadowInvoice,
    Subscription,
    utcnow,
)
from app.services import audit
from app.services.metering import list_event_ids_for_period, sum_usage
from app.services.pricing import get_version, price_quantity


def _next_invoice_number(db: Session, organization_id: str) -> str:
    """Allocate the next human-readable invoice number for an organization.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant id.

    Returns:
        Invoice number string such as ``INV-000001``.
    """
    count = db.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.organization_id == organization_id)
    )
    return f"INV-{(count or 0) + 1:06d}"


def _is_immutable(invoice: Invoice) -> bool:
    """Return whether invoice line totals must not be rewritten.

    Args:
        invoice: Invoice to inspect.

    Returns:
        ``True`` when finalized or in a terminal accounting status.
    """
    if invoice.finalized_at is not None:
        return True
    return invoice.status in {
        InvoiceStatus.open,
        InvoiceStatus.paid,
        InvoiceStatus.finalized,
        InvoiceStatus.void,
        InvoiceStatus.uncollectible,
    }


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
    """Generate or return an idempotent invoice for a customer period.

    Finalized invoices are never rewritten. Draft invoices may be recalculated.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant id.
        customer_id: Customer primary key.
        period_start: Inclusive UTC period start.
        period_end: Inclusive UTC period end.
        subscription_id: Optional subscription override.
        finalize: When True, mark the invoice open/finalized.
        actor_user_id: Optional authenticated user id for audit.

    Returns:
        ``Invoice`` with lines and totals.

    Raises:
        ValueError: Missing customer/subscription or invalid period.
    """
    if period_end < period_start:
        raise ValueError("period_end must be >= period_start")

    existing = db.scalar(
        select(Invoice).where(
            Invoice.organization_id == organization_id,
            Invoice.customer_id == customer_id,
            Invoice.period_start == period_start,
            Invoice.period_end == period_end,
        )
    )
    if existing is not None:
        if _is_immutable(existing) or existing.status != InvoiceStatus.draft:
            return existing
        # Draft may be rebuilt by deleting lines and recalculating.
        for line in list(existing.lines):
            db.delete(line)
        db.flush()
        invoice = existing
    else:
        invoice = None

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
    if invoice is None:
        invoice = Invoice(
            organization_id=organization_id,
            customer_id=customer_id,
            subscription_id=subscription.id,
            pricing_version_id=version.id,
            number=_next_invoice_number(db, organization_id),
            status=InvoiceStatus.draft,
            currency=customer.currency,
            period_start=period_start,
            period_end=period_end,
            tax_total=money(0),  # tax extension point — always zero here
        )
        db.add(invoice)
        try:
            with db.begin_nested():
                db.flush()
        except IntegrityError:
            existing = db.scalar(
                select(Invoice).where(
                    Invoice.organization_id == organization_id,
                    Invoice.customer_id == customer_id,
                    Invoice.period_start == period_start,
                    Invoice.period_end == period_end,
                )
            )
            if existing is None:
                raise
            return existing
    else:
        invoice.pricing_version_id = version.id
        invoice.subscription_id = subscription.id

    amounts: list[Decimal] = []
    base = money(version.base_fee)
    if base:
        line = InvoiceLine(
            invoice_id=invoice.id,
            pricing_version_id=version.id,
            description="Base subscription fee",
            quantity=Decimal("1"),
            unit_price=base,
            amount=base,
        )
        db.add(line)
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
        event_ids = list_event_ids_for_period(
            db,
            organization_id=organization_id,
            customer_id=customer_id,
            metric_id=component.metric_id,
            period_start=period_start,
            period_end=period_end,
        )
        desc = f"Usage: {metric.code if metric else component.metric_id}"
        line = InvoiceLine(
            invoice_id=invoice.id,
            metric_id=component.metric_id,
            pricing_version_id=version.id,
            description=desc,
            quantity=qty,
            unit_price=unit,
            amount=amount,
            source_event_ids_json=json.dumps(event_ids),
        )
        db.add(line)
        amounts.append(amount)

    invoice.subtotal = sum_money(amounts)
    invoice.tax_total = money(0)
    invoice.total = money(invoice.subtotal + invoice.tax_total)

    if finalize:
        invoice.status = InvoiceStatus.open
        invoice.finalized_at = utcnow()

    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="invoice.generate",
        entity_type="invoice",
        entity_id=invoice.id,
        details={
            "number": invoice.number,
            "total": str(invoice.total),
            "finalized": finalize,
            "correlation_id": invoice.correlation_id,
        },
    )
    return invoice


def assert_mutable(invoice: Invoice) -> None:
    """Raise if the invoice is immutable.

    Args:
        invoice: Invoice to check.

    Raises:
        InvoiceImmutableError: When the invoice is finalized.
    """
    if _is_immutable(invoice):
        raise InvoiceImmutableError(invoice.id)


def shadow_compare(
    db: Session,
    *,
    organization_id: str,
    invoice_id: str,
    alternate_pricing_version_id: str,
    expected_delta: Decimal | None = None,
    actor_user_id: str | None = None,
) -> ShadowInvoice:
    """Compare an invoice against an alternate pricing version on frozen usage.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant id.
        invoice_id: Source invoice id.
        alternate_pricing_version_id: Candidate pricing version.
        expected_delta: Optional declared delta that classifies as expected.
        actor_user_id: Optional authenticated user id for audit.

    Returns:
        ``ShadowInvoice`` with classification and cutover flag.

    Raises:
        ValueError: If the invoice is missing.
    """
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
        # Late adjustments are excluded from sum_usage; shadow uses same frozen usage set.
        _, amount = price_quantity(component, qty)
        amounts.append(amount)
    total = sum_money(amounts)
    delta = money(total - money(invoice.total))
    tolerance = money(get_settings().shadow_expected_tolerance)

    if abs(delta) <= tolerance:
        classification = "match"
        cutover_allowed = True
        notes = "totals match within tolerance"
    elif expected_delta is not None and money(expected_delta) == delta:
        classification = "expected_delta"
        cutover_allowed = True
        notes = f"delta matches declared expected_delta={expected_delta}"
    else:
        classification = "unexpected_delta"
        cutover_allowed = False
        notes = (
            f"unexpected delta={delta}; declare expected_delta or investigate pricing/usage "
            "before cutover"
        )

    shadow = ShadowInvoice(
        organization_id=organization_id,
        customer_id=invoice.customer_id,
        source_invoice_id=invoice.id,
        pricing_version_id=alt.id,
        total=total,
        delta=delta,
        classification=classification,
        cutover_allowed=cutover_allowed,
        notes=notes,
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
        details={
            "source": invoice.id,
            "delta": str(delta),
            "classification": classification,
            "cutover_allowed": cutover_allowed,
        },
    )
    return shadow


def execute_cutover(
    db: Session,
    *,
    organization_id: str,
    plan_code: str,
    to_pricing_version_id: str,
    invoice_ids: list[str],
    actor_user_id: str | None = None,
) -> PricingCutover:
    """Cut over active subscriptions when shadow comparisons allow it.

    Does not mutate finalized invoices or re-issue payments.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant id.
        plan_code: Plan code to cut over.
        to_pricing_version_id: Target pricing version id.
        invoice_ids: Invoices whose shadows must allow cutover.
        actor_user_id: Optional authenticated user id for audit.

    Returns:
        ``PricingCutover`` audit row with action ``cutover``.

    Raises:
        CutoverBlockedError: When any listed shadow forbids cutover.
        ValueError: Invalid plan/version pairing.
    """
    plan = db.scalar(
        select(PricingPlan).where(
            PricingPlan.organization_id == organization_id,
            PricingPlan.code == plan_code,
        )
    )
    if plan is None:
        raise ValueError("plan not found")
    to_version = get_version(db, to_pricing_version_id)
    if to_version.plan_id != plan.id:
        raise ValueError("to_pricing_version_id does not belong to plan")

    report: list[dict] = []
    blocked = False
    for invoice_id in invoice_ids:
        shadow = db.scalar(
            select(ShadowInvoice)
            .where(
                ShadowInvoice.organization_id == organization_id,
                ShadowInvoice.source_invoice_id == invoice_id,
                ShadowInvoice.pricing_version_id == to_pricing_version_id,
            )
            .order_by(ShadowInvoice.created_at.desc())
        )
        if shadow is None or not shadow.cutover_allowed:
            blocked = True
            report.append(
                {
                    "invoice_id": invoice_id,
                    "cutover_allowed": False,
                    "classification": None if shadow is None else shadow.classification,
                }
            )
        else:
            report.append(
                {
                    "invoice_id": invoice_id,
                    "cutover_allowed": True,
                    "classification": shadow.classification,
                    "delta": str(shadow.delta),
                }
            )

    from_version_id = (
        sorted(plan.versions, key=lambda v: v.version)[-2].id
        if len(plan.versions) >= 2
        else to_version.id
    )

    if blocked:
        cutover = PricingCutover(
            organization_id=organization_id,
            plan_id=plan.id,
            from_version_id=from_version_id,
            to_version_id=to_version.id,
            action="blocked",
            shadow_report_json=json.dumps(report),
        )
        db.add(cutover)
        db.flush()
        raise CutoverBlockedError("one or more invoices have unexpected shadow deltas")

    # Move active subscriptions on this plan to the new version (forward-looking only).
    subs = db.scalars(
        select(Subscription).where(
            Subscription.organization_id == organization_id,
            Subscription.plan_id == plan.id,
            Subscription.status == "active",
        )
    ).all()
    for sub in subs:
        sub.pricing_version_id = to_version.id

    cutover = PricingCutover(
        organization_id=organization_id,
        plan_id=plan.id,
        from_version_id=from_version_id,
        to_version_id=to_version.id,
        action="cutover",
        shadow_report_json=json.dumps(report),
    )
    db.add(cutover)
    db.flush()
    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="pricing.cutover",
        entity_type="pricing_cutover",
        entity_id=cutover.id,
        details={"plan_code": plan_code, "to_version": to_version.id},
    )
    return cutover


def rollback_cutover(
    db: Session,
    *,
    organization_id: str,
    cutover_id: str,
    actor_user_id: str | None = None,
) -> PricingCutover:
    """Roll back a successful cutover by restoring prior subscription versions.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant id.
        cutover_id: Prior cutover row id.
        actor_user_id: Optional authenticated user id for audit.

    Returns:
        New ``PricingCutover`` row with action ``rollback``.

    Raises:
        ValueError: If the cutover is missing or not rollback-eligible.
    """
    prior = db.get(PricingCutover, cutover_id)
    if prior is None or prior.organization_id != organization_id:
        raise ValueError("cutover not found")
    if prior.action != "cutover":
        raise ValueError("can only roll back a successful cutover")

    subs = db.scalars(
        select(Subscription).where(
            Subscription.organization_id == organization_id,
            Subscription.plan_id == prior.plan_id,
            Subscription.status == "active",
        )
    ).all()
    for sub in subs:
        sub.pricing_version_id = prior.from_version_id

    row = PricingCutover(
        organization_id=organization_id,
        plan_id=prior.plan_id,
        from_version_id=prior.to_version_id,
        to_version_id=prior.from_version_id,
        action="rollback",
        shadow_report_json=prior.shadow_report_json,
    )
    db.add(row)
    db.flush()
    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="pricing.rollback",
        entity_type="pricing_cutover",
        entity_id=row.id,
        details={"restored_version": prior.from_version_id},
    )
    return row


def list_adjustments(db: Session, invoice_id: str) -> list[InvoiceAdjustment]:
    """List late-usage adjustments for an invoice.

    Args:
        db: Active SQLAlchemy session.
        invoice_id: Invoice primary key.

    Returns:
        List of ``InvoiceAdjustment`` rows.
    """
    return list(
        db.scalars(select(InvoiceAdjustment).where(InvoiceAdjustment.invoice_id == invoice_id)).all()
    )
