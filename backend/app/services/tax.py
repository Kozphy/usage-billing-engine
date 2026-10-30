"""Tax calculation extension point.

This portfolio build intentionally does not compute tax. Callers should leave
``Invoice.tax_total`` at zero. A future adapter can implement jurisdiction
rules here without changing usage metering or payment-status storage.
"""

from __future__ import annotations

from decimal import Decimal

from app.money import money


def calculate_tax(*, taxable_subtotal: Decimal, currency: str = "USD") -> Decimal:
    """Return tax amount for a subtotal.

    Currently always ``0`` (extension point only).

    Args:
        taxable_subtotal: Invoice subtotal before tax.
        currency: ISO currency code (unused in this stub).

    Returns:
        Quantized tax amount (always zero in this build).
    """
    _ = (taxable_subtotal, currency)
    return money(0)
