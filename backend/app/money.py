"""Decimal money helpers.

Floats are rejected so IEEE binary rounding cannot enter invoices or ledgers.

Two scales exist on purpose:

* Catalog rates and ``Numeric(20, 4)`` columns use ``MONEY_QUANTUM`` (0.0001).
  ``money()`` quantizes onto that storage grid when a rate is saved.
* Each invoice line is rounded once, from the exact extended amount, to the
  currency's ISO 4217 minor unit (``ROUND_HALF_EVEN``). Invoice totals are the
  exact sum of those posted lines. Provider charges use integer minor units.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from app.currencies import UnknownCurrencyError, minor_unit_places, normalize_currency

MONEY_QUANTUM = Decimal("0.0001")
DISPLAY_QUANTUM = Decimal("0.01")
USAGE_QUANTUM = Decimal("0.000001")
ZERO = Decimal("0")

__all__ = [
    "DISPLAY_QUANTUM",
    "MONEY_QUANTUM",
    "USAGE_QUANTUM",
    "ZERO",
    "UnknownCurrencyError",
    "currency_quantum",
    "display",
    "invoice_amount",
    "is_zero",
    "minor_unit_places",
    "money",
    "normalize_currency",
    "round_money",
    "sum_money",
    "to_minor_units",
    "usage_qty",
]


def _decimal(value: Decimal | int | str) -> Decimal:
    """Convert a non-float accounting value to ``Decimal``.

    Args:
        value: Amount as ``Decimal``, ``int``, or numeric ``str``.

    Returns:
        Exact ``Decimal`` conversion.

    Raises:
        TypeError: If ``value`` is a ``float``.
        ValueError: If ``value`` cannot be converted to ``Decimal``.
    """
    if isinstance(value, float):
        raise TypeError("float is not allowed for accounting amounts; use Decimal or str")
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid money value {value!r}") from exc


def money(value: Decimal | int | str) -> Decimal:
    """Quantize a catalog or storage amount to the column quantum.

    This is the ``Numeric(20, 4)`` grid, not invoice rounding. Invoice lines
    use ``invoice_amount`` so a currency minor unit is applied once.

    Args:
        value: Amount as ``Decimal``, ``int``, or numeric ``str``. Floats are
            not accepted.

    Returns:
        ``Decimal`` quantized to ``MONEY_QUANTUM`` (0.0001) with
        ``ROUND_HALF_EVEN``.

    Raises:
        TypeError: If ``value`` is a ``float``.
        ValueError: If ``value`` cannot be converted to ``Decimal``.
    """
    return _decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_EVEN)


def currency_quantum(currency: str) -> Decimal:
    """Return the minor-unit quantum for ``currency`` (``1``, ``0.01``, ``0.001``, …).

    Args:
        currency: ISO 4217 alphabetic code.

    Returns:
        Positive ``Decimal`` equal to one minor unit.

    Raises:
        UnknownCurrencyError: If ``currency`` is not in the ISO table.
    """
    places = minor_unit_places(currency)
    return Decimal(1).scaleb(-places)


def round_money(value: Decimal | int | str, currency: str) -> Decimal:
    """Round an amount once to the currency minor unit.

    Args:
        value: Amount as ``Decimal``, ``int``, or numeric ``str``.
        currency: ISO 4217 alphabetic code.

    Returns:
        Amount quantized with ``ROUND_HALF_EVEN`` to ``currency_quantum``.

    Raises:
        TypeError: If ``value`` is a ``float``.
        UnknownCurrencyError: If ``currency`` is unknown.
        ValueError: If ``value`` cannot be converted to ``Decimal``.
    """
    quantum = currency_quantum(currency)
    return _decimal(value).quantize(quantum, rounding=ROUND_HALF_EVEN)


def invoice_amount(value: Decimal | int | str, currency: str) -> Decimal:
    """Round once for a posted invoice amount and align to storage scale.

    Alignment to ``MONEY_QUANTUM`` does not round again: every exponent in the
    ISO table is at most 4, so a currency-rounded amount is already a multiple
    of 0.0001. Persisted values keep four decimal places (trailing zeros) so
    existing ``Numeric(20, 4)`` columns and API decimals stay stable.

    Args:
        value: Exact extended amount.
        currency: ISO 4217 alphabetic code of the invoice.

    Returns:
        Posted amount, numerically equal to ``round_money`` and scaled to
        ``MONEY_QUANTUM``.

    Raises:
        TypeError: If ``value`` is a ``float``.
        UnknownCurrencyError: If ``currency`` is unknown.
        ValueError: If the rounded amount does not fit the storage quantum.
    """
    rounded = round_money(value, currency)
    posted = rounded.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_EVEN)
    if posted != rounded:
        code = normalize_currency(currency)
        raise ValueError(
            f"rounded {code} amount {rounded} does not fit storage quantum {MONEY_QUANTUM}"
        )
    return posted


def to_minor_units(value: Decimal | int | str, currency: str) -> int:
    """Convert a major-unit amount to an integer count of minor units.

    The amount is rounded once with ``ROUND_HALF_EVEN`` before scaling, so
    JPY 500 stays 500, USD 10.00 becomes 1000, KWD 1.234 becomes 1234, and
    TWD 10.50 becomes 1050 (ISO exponent 2).

    Args:
        value: Major-unit amount.
        currency: ISO 4217 alphabetic code.

    Returns:
        Integer minor units suitable for a payment-provider ``amount`` field.

    Raises:
        TypeError: If ``value`` is a ``float``.
        UnknownCurrencyError: If ``currency`` is unknown.
        ValueError: If the scaled amount is not an integer.
    """
    rounded = round_money(value, currency)
    places = minor_unit_places(currency)
    scaled = rounded.scaleb(places)
    integral = scaled.to_integral_value(rounding=ROUND_HALF_EVEN)
    if integral != scaled:
        code = normalize_currency(currency)
        raise ValueError(f"amount {rounded} for {code} did not convert to integer minor units")
    return int(integral)


def usage_qty(value: Decimal | int | str) -> Decimal:
    """Quantize a non-negative usage quantity.

    Args:
        value: Quantity as ``Decimal``, ``int``, or numeric ``str``. Floats are
            not accepted.

    Returns:
        ``Decimal`` quantized to ``USAGE_QUANTUM`` (0.000001).

    Raises:
        TypeError: If ``value`` is a ``float``.
        ValueError: If ``value`` is invalid or negative.
    """
    if isinstance(value, float):
        raise TypeError("float is not allowed for usage quantities; use Decimal or str")
    try:
        quantized = Decimal(value).quantize(USAGE_QUANTUM, rounding=ROUND_HALF_EVEN)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid usage quantity {value!r}") from exc
    if quantized < ZERO:
        raise ValueError("usage quantity cannot be negative")
    return quantized


def display(value: Decimal | int | str, currency: str = "USD") -> str:
    """Format an amount at the currency's minor-unit scale.

    Args:
        value: Amount to format.
        currency: ISO 4217 alphabetic code. Defaults to USD (2 decimal places).

    Returns:
        String rounded once with ``ROUND_HALF_EVEN``. JPY has no decimal
        places; KWD has three; USD and TWD have two.

    Raises:
        TypeError: If ``value`` is a ``float``.
        UnknownCurrencyError: If ``currency`` is unknown.
    """
    rounded = round_money(value, currency)
    places = minor_unit_places(currency)
    return f"{rounded:.{places}f}"


def is_zero(value: Decimal | int | str) -> bool:
    """Return whether ``money(value)`` equals the storage-grid zero.

    Args:
        value: Amount to test (``Decimal``, ``int``, or numeric ``str``).

    Returns:
        ``True`` if the storage-quantized amount equals ``ZERO``.
    """
    return money(value) == ZERO


def sum_money(values: list[Decimal]) -> Decimal:
    """Sum amounts at full precision, without rounding each addend.

    Invoice totals must equal the sum of lines that were already rounded.
    This function does not quantize intermediate sums. Callers that need a
    currency minor unit round each line with ``invoice_amount`` first.

    Args:
        values: Money-compatible amounts. Floats are rejected.

    Returns:
        Exact ``Decimal`` sum.

    Raises:
        TypeError: If any value is a ``float``.
        ValueError: If a value cannot be converted to ``Decimal``.
    """
    total = ZERO
    for value in values:
        total += _decimal(value)
    return total
