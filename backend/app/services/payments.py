"""Payment provider adapters and idempotent charge/refund orchestration."""

from __future__ import annotations

import hashlib
import hmac
import random
from decimal import Decimal
from typing import Protocol
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_setup import get_logger
from app.money import invoice_amount, normalize_currency, to_minor_units
from app.models import Invoice, InvoiceStatus, PaymentAttempt, Refund, utcnow
from app.services import audit

log = get_logger(__name__)


def minor_unit_charge(amount: Decimal, currency: str) -> tuple[int, str]:
    """Convert a charge or refund into provider minor units.

    Args:
        amount: Major-unit amount. Rounded once to the currency quantum.
        currency: ISO 4217 alphabetic code.

    Returns:
        ``(minor_units, canonical_currency)``. ``minor_units`` is the integer
        sent as the provider ``amount`` (USD cents, JPY yen, KWD fils, TWD
        cents per ISO exponent 2).

    Raises:
        UnknownCurrencyError: If ``currency`` is unknown.
        TypeError: If ``amount`` is a float.
    """
    code = normalize_currency(currency)
    return to_minor_units(amount, code), code


class PaymentProvider(Protocol):
    """Protocol for charge/refund adapters (mock or Stripe)."""

    name: str

    def charge(
        self,
        *,
        invoice: Invoice,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> dict:
        """Charge an invoice amount.

        Args:
            invoice: Invoice being charged.
            amount: Quantized charge amount.
            currency: ISO currency code.
            idempotency_key: Provider idempotency key.

        Returns:
            Provider result dict with ``status`` and ``provider_payment_id``.
        """
        ...

    def refund(
        self,
        *,
        invoice: Invoice,
        amount: Decimal,
        reason: str,
    ) -> dict:
        """Refund a previously charged invoice.

        Args:
            invoice: Paid invoice.
            amount: Major-unit refund amount, sent as integer minor units.
            reason: Human-readable refund reason.

        Returns:
            Provider result dict with ``provider_refund_id``.
        """
        ...


class MockPaymentProvider:
    """Deterministic local fake for offline tests. Never talks to a network."""

    name = "mock"

    def charge(
        self,
        *,
        invoice: Invoice,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> dict:
        """Return a deterministic successful fake charge.

        Args:
            invoice: Invoice being charged.
            amount: Quantized charge amount.
            currency: ISO currency code.
            idempotency_key: Used to build a stable fake payment id.

        Returns:
            Fake provider result with ``mode=fake``.

        Raises:
            TimeoutError: When ``mock_payment_timeout_rate`` triggers.
        """
        settings = get_settings()
        if settings.mock_payment_timeout_rate > 0 and random.random() < settings.mock_payment_timeout_rate:
            raise TimeoutError("simulated mock provider timeout")
        minor, code = minor_unit_charge(amount, currency)
        return {
            "provider_payment_id": f"mock_pay_{idempotency_key[:16]}",
            "status": "succeeded",
            "amount": str(minor),
            "amount_minor": minor,
            "currency": code,
            "mode": "fake",
        }

    def refund(self, *, invoice: Invoice, amount: Decimal, reason: str) -> dict:
        """Return a deterministic successful fake refund.

        Args:
            invoice: Paid invoice.
            amount: Major-unit refund amount, sent as integer minor units.
            reason: Human-readable refund reason.

        Returns:
            Fake provider refund result with ``mode=fake``.
        """
        minor, code = minor_unit_charge(amount, invoice.currency)
        return {
            "provider_refund_id": f"mock_ref_{invoice.id[:8]}",
            "status": "succeeded",
            "amount": str(minor),
            "amount_minor": minor,
            "currency": code,
            "reason": reason,
            "mode": "fake",
        }


class StripeAdapter:
    """Stripe test-mode via HTTPS when STRIPE_SECRET_KEY is set.

    Without a key this adapter refuses. Card data is never collected or stored —
    PaymentIntents are created server-side with amount + currency only.
    """

    name = "stripe"
    api_base = "https://api.stripe.com/v1"

    def charge(
        self,
        *,
        invoice: Invoice,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> dict:
        """Create and confirm a Stripe test-mode PaymentIntent.

        Args:
            invoice: Invoice being charged.
            amount: Major-unit charge amount, sent as integer minor units.
            currency: ISO currency code.
            idempotency_key: Stripe ``Idempotency-Key`` header value.

        Returns:
            Provider result including Stripe payment intent id.

        Raises:
            RuntimeError: Missing secret key or Stripe API error.
            TimeoutError: Provider request timed out.
        """
        settings = get_settings()
        if not settings.stripe_secret_key:
            raise RuntimeError(
                "STRIPE_SECRET_KEY not configured; use PAYMENT_PROVIDER=mock for local demos"
            )
        minor, code = minor_unit_charge(amount, currency)
        data = {
            "amount": str(minor),
            "currency": code.lower(),
            "confirm": "true",
            "payment_method": "pm_card_visa",  # Stripe test PM — not a real card PAN
            "metadata[invoice_id]": invoice.id,
            "metadata[mode]": "test",
        }
        try:
            response = httpx.post(
                f"{self.api_base}/payment_intents",
                content=urlencode(data),
                headers={
                    "Authorization": f"Bearer {settings.stripe_secret_key}",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Idempotency-Key": idempotency_key,
                },
                timeout=15.0,
            )
        except httpx.TimeoutException as exc:
            raise TimeoutError("stripe provider timeout") from exc
        if response.status_code >= 400:
            raise RuntimeError(f"stripe error: {response.status_code} {response.text[:200]}")
        body = response.json()
        status = body.get("status", "failed")
        mapped = "succeeded" if status == "succeeded" else status
        return {
            "provider_payment_id": body.get("id"),
            "status": mapped,
            "amount": str(minor),
            "amount_minor": minor,
            "currency": code,
            "mode": "stripe_test",
            "raw_status": status,
        }

    def refund(self, *, invoice: Invoice, amount: Decimal, reason: str) -> dict:
        """Create a Stripe refund against the invoice payment intent.

        Args:
            invoice: Paid invoice with ``provider_invoice_id`` when available.
            amount: Major-unit refund amount, sent as integer minor units.
            reason: Human-readable refund reason.

        Returns:
            Provider refund result with ``mode=stripe_test``.

        Raises:
            RuntimeError: Missing secret key or Stripe API error.
        """
        settings = get_settings()
        if not settings.stripe_secret_key:
            raise RuntimeError("STRIPE_SECRET_KEY not configured")
        minor, code = minor_unit_charge(amount, invoice.currency)
        data = {"amount": str(minor), "reason": "requested_by_customer"}
        if invoice.provider_invoice_id:
            data["payment_intent"] = invoice.provider_invoice_id
        response = httpx.post(
            f"{self.api_base}/refunds",
            content=urlencode(data),
            headers={
                "Authorization": f"Bearer {settings.stripe_secret_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=15.0,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"stripe refund error: {response.status_code}")
        body = response.json()
        return {
            "provider_refund_id": body.get("id"),
            "status": body.get("status", "succeeded"),
            "amount": str(minor),
            "amount_minor": minor,
            "currency": code,
            "reason": reason,
            "mode": "stripe_test",
        }


def get_provider() -> PaymentProvider:
    """Return the configured payment provider adapter.

    Returns:
        ``StripeAdapter`` when ``PAYMENT_PROVIDER=stripe``, otherwise mock.
    """
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
    """Charge an open invoice idempotently.

    Payment status is stored separately from invoice calculation totals.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant id.
        invoice_id: Invoice to charge.
        idempotency_key: Unique key preventing duplicate provider requests.
        actor_user_id: Optional authenticated user id for audit.

    Returns:
        ``PaymentAttempt`` row (existing row returned on idempotent retry).

    Raises:
        ValueError: Invoice missing, not chargeable, or already paid without attempt.
    """
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
    if invoice.status not in {InvoiceStatus.open, InvoiceStatus.finalized}:
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
    currency = normalize_currency(invoice.currency)
    posted = invoice_amount(invoice.total, currency)
    attempt = PaymentAttempt(
        organization_id=organization_id,
        invoice_id=invoice.id,
        provider=provider.name,
        amount=posted,
        currency=currency,
        status="pending",
        idempotency_key=idempotency_key,
        correlation_id=invoice.correlation_id,
    )
    db.add(attempt)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        prior = db.scalar(
            select(PaymentAttempt).where(
                PaymentAttempt.organization_id == organization_id,
                PaymentAttempt.idempotency_key == idempotency_key,
            )
        )
        if prior is None:
            raise
        return prior

    try:
        result = provider.charge(
            invoice=invoice,
            amount=posted,
            currency=currency,
            idempotency_key=idempotency_key,
        )
        attempt.provider_payment_id = result.get("provider_payment_id")
        attempt.status = result.get("status", "failed")
        if attempt.status == "succeeded":
            # Payment state only — invoice line totals remain the finalized calculation.
            invoice.status = InvoiceStatus.paid
            invoice.paid_at = utcnow()
            invoice.provider_invoice_id = attempt.provider_payment_id
    except TimeoutError as exc:
        attempt.status = "timed_out"
        attempt.last_error = str(exc)
        log.warning(
            "payment_timeout",
            extra={
                "payment_attempt_id": attempt.id,
                "invoice_id": invoice.id,
                "organization_id": organization_id,
            },
        )
    except Exception as exc:  # noqa: BLE001
        attempt.status = "failed"
        attempt.last_error = str(exc)

    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="payment.charge",
        entity_type="payment_attempt",
        entity_id=attempt.id,
        details={
            "status": attempt.status,
            "invoice_id": invoice.id,
            "correlation_id": attempt.correlation_id,
        },
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
    """Refund part or all of a paid invoice.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant id.
        invoice_id: Paid invoice id.
        amount: Refund amount (must be > 0 and <= invoice total).
        reason: Human-readable refund reason.
        actor_user_id: Optional authenticated user id for audit.

    Returns:
        Persisted ``Refund`` row.

    Raises:
        ValueError: Invoice not paid or amount out of range.
    """
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.organization_id != organization_id:
        raise ValueError("invoice not found")
    if invoice.status != InvoiceStatus.paid:
        raise ValueError("only paid invoices can be refunded")
    currency = normalize_currency(invoice.currency)
    amt = invoice_amount(amount, currency)
    if Decimal(amount) != amt:
        raise ValueError(
            f"refund amount {amount} is not aligned to {currency} minor units ({amt})"
        )
    total = invoice_amount(invoice.total, currency)
    if amt <= 0 or amt > total:
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
    """Verify a Stripe-like webhook signature header (``t=...,v1=...``).

    Args:
        payload: Raw request body bytes.
        signature_header: ``Stripe-Signature`` header value.
        secret: Webhook signing secret.

    Returns:
        ``True`` when the HMAC matches.
    """
    parts = dict(item.split("=", 1) for item in signature_header.split(",") if item.count("=") == 1)
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
    """Apply an idempotent paid status update from a provider webhook.

    Out-of-order deliveries are safe: already-paid invoices are no-ops.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant id.
        provider_payment_id: Provider payment identifier.
        payload: Parsed webhook JSON (may include ``invoice_id`` fallback).

    Returns:
        Updated ``Invoice`` or ``None`` when no matching invoice is found.
    """
    attempt = db.scalar(
        select(PaymentAttempt).where(
            PaymentAttempt.organization_id == organization_id,
            PaymentAttempt.provider_payment_id == provider_payment_id,
        )
    )
    if attempt is None:
        invoice_id = payload.get("invoice_id")
        invoice = db.get(Invoice, invoice_id) if invoice_id else None
    else:
        invoice = db.get(Invoice, attempt.invoice_id)
        if attempt.status != "succeeded":
            attempt.status = "succeeded"
    if invoice is None:
        return None
    if invoice.status == InvoiceStatus.paid:
        return invoice
    invoice.status = InvoiceStatus.paid
    invoice.paid_at = utcnow()
    invoice.provider_invoice_id = provider_payment_id
    return invoice
