from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.money import money
from app.models import Invoice, InvoiceStatus, PaymentAttempt, Refund, utcnow
from app.services import audit


class PaymentProvider(Protocol):
    name: str

    def charge(
        self,
        *,
        invoice: Invoice,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> dict: ...

    def refund(
        self,
        *,
        invoice: Invoice,
        amount: Decimal,
        reason: str,
    ) -> dict: ...


class MockPaymentProvider:
    name = "mock"

    def charge(
        self,
        *,
        invoice: Invoice,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> dict:
        return {
            "provider_payment_id": f"mock_pay_{idempotency_key[:16]}",
            "status": "succeeded",
            "amount": str(money(amount)),
            "currency": currency,
        }

    def refund(self, *, invoice: Invoice, amount: Decimal, reason: str) -> dict:
        return {
            "provider_refund_id": f"mock_ref_{invoice.id[:8]}",
            "status": "succeeded",
            "amount": str(money(amount)),
            "reason": reason,
        }


class StripeAdapter:
    """Thin adapter — requires STRIPE_SECRET_KEY. Without it, raises clearly."""

    name = "stripe"

    def charge(
        self,
        *,
        invoice: Invoice,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> dict:
        settings = get_settings()
        if not settings.stripe_secret_key:
            raise RuntimeError(
                "STRIPE_SECRET_KEY not configured; use PAYMENT_PROVIDER=mock for local demos"
            )
        # Intentional stub: real Stripe SDK call would go here when keys are present.
        # Verified path is mock until keys exist (portfolio constraint).
        raise RuntimeError("Stripe live charge not enabled in this portfolio build")

    def refund(self, *, invoice: Invoice, amount: Decimal, reason: str) -> dict:
        raise RuntimeError("Stripe live refund not enabled in this portfolio build")


def get_provider() -> PaymentProvider:
    settings = get_settings()
    if settings.payment_provider == "stripe":
        return StripeAdapter()
    return MockPaymentProvider()


def charge_invoice(
    db: Session,
    *,
    organization_id: str,
    invoice_id: str,
    idempotency_key: str,
    actor_user_id: str | None = None,
) -> PaymentAttempt:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.organization_id != organization_id:
        raise ValueError("invoice not found")
    if invoice.status == InvoiceStatus.paid:
        existing = db.scalar(
            select(PaymentAttempt).where(
                PaymentAttempt.organization_id == organization_id,
                PaymentAttempt.invoice_id == invoice_id,
                PaymentAttempt.status == "succeeded",
            )
        )
        if existing:
            return existing
        raise ValueError("invoice already paid")
    if invoice.status not in {InvoiceStatus.open, InvoiceStatus.draft}:
        raise ValueError(f"cannot charge invoice in status {invoice.status}")

    prior = db.scalar(
        select(PaymentAttempt).where(
            PaymentAttempt.organization_id == organization_id,
            PaymentAttempt.idempotency_key == idempotency_key,
        )
    )
    if prior is not None:
        return prior

    provider = get_provider()
    attempt = PaymentAttempt(
        organization_id=organization_id,
        invoice_id=invoice.id,
        provider=provider.name,
        amount=money(invoice.total),
        currency=invoice.currency,
        status="pending",
        idempotency_key=idempotency_key,
    )
    db.add(attempt)
    db.flush()

    result = provider.charge(
        invoice=invoice,
        amount=money(invoice.total),
        currency=invoice.currency,
        idempotency_key=idempotency_key,
    )
    attempt.provider_payment_id = result.get("provider_payment_id")
    attempt.status = result.get("status", "failed")
    if attempt.status == "succeeded":
        invoice.status = InvoiceStatus.paid
        invoice.paid_at = utcnow()
        invoice.provider_invoice_id = attempt.provider_payment_id
    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="payment.charge",
        entity_type="payment_attempt",
        entity_id=attempt.id,
        details={"status": attempt.status, "invoice_id": invoice.id},
    )
    return attempt


def refund_invoice(
    db: Session,
    *,
    organization_id: str,
    invoice_id: str,
    amount: Decimal,
    reason: str = "",
    actor_user_id: str | None = None,
) -> Refund:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.organization_id != organization_id:
        raise ValueError("invoice not found")
    if invoice.status != InvoiceStatus.paid:
        raise ValueError("only paid invoices can be refunded")
    amt = money(amount)
    if amt <= 0 or amt > money(invoice.total):
        raise ValueError("refund amount out of range")
    provider = get_provider()
    result = provider.refund(invoice=invoice, amount=amt, reason=reason)
    row = Refund(
        organization_id=organization_id,
        invoice_id=invoice.id,
        amount=amt,
        reason=reason,
        provider_refund_id=result.get("provider_refund_id"),
    )
    db.add(row)
    db.flush()
    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="payment.refund",
        entity_type="refund",
        entity_id=row.id,
        details={"amount": str(amt)},
    )
    return row


def verify_stripe_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """Minimal Stripe-like HMAC verification for demo webhooks (t=...,v1=...)."""
    parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        return False
    signed = f"{timestamp}.".encode() + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def mark_paid_from_webhook(
    db: Session,
    *,
    organization_id: str,
    provider_payment_id: str,
    payload: dict,
) -> Invoice | None:
    attempt = db.scalar(
        select(PaymentAttempt).where(
            PaymentAttempt.organization_id == organization_id,
            PaymentAttempt.provider_payment_id == provider_payment_id,
        )
    )
    if attempt is None:
        # Fallback: invoice id in payload
        invoice_id = payload.get("invoice_id")
        invoice = db.get(Invoice, invoice_id) if invoice_id else None
    else:
        invoice = db.get(Invoice, attempt.invoice_id)
        attempt.status = "succeeded"
    if invoice is None:
        return None
    invoice.status = InvoiceStatus.paid
    invoice.paid_at = utcnow()
    invoice.provider_invoice_id = provider_payment_id
    return invoice
