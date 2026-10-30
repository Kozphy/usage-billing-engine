from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.money import money, sum_money
from app.models import Customer, Invoice, InvoiceStatus, UsageEvent
from app.schemas import ReportSummaryOut


def summary(db: Session, organization_id: str) -> ReportSummaryOut:
    customers = db.scalar(
        select(func.count()).select_from(Customer).where(Customer.organization_id == organization_id)
    ) or 0
    usage_events = db.scalar(
        select(func.count())
        .select_from(UsageEvent)
        .where(UsageEvent.organization_id == organization_id)
    ) or 0
    open_invoices = db.scalars(
        select(Invoice).where(
            Invoice.organization_id == organization_id,
            Invoice.status == InvoiceStatus.open,
        )
    ).all()
    paid_invoices = db.scalars(
        select(Invoice).where(
            Invoice.organization_id == organization_id,
            Invoice.status == InvoiceStatus.paid,
        )
    ).all()
    return ReportSummaryOut(
        customers=customers,
        usage_events=usage_events,
        invoices_open=len(open_invoices),
        invoices_paid=len(paid_invoices),
        revenue_paid=sum_money([money(i.total) for i in paid_invoices]) if paid_invoices else Decimal("0"),
        revenue_open=sum_money([money(i.total) for i in open_invoices]) if open_invoices else Decimal("0"),
    )
