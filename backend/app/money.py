"""Decimal money helpers adapted from FinOps control-plane patterns.

Floats are rejected so IEEE binary rounding cannot enter invoices or ledgers.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

MONEY_QUANTUM = Decimal("0.0001")
DISPLAY_QUANTUM = Decimal("0.01")
USAGE_QUANTUM = Decimal("0.000001")
ZERO = Decimal("0")


def money(value: Decimal | int | str) -> Decimal:
    if isinstance(value, float):
        raise TypeError("float is not allowed for accounting amounts; use Decimal or str")
    try:
        return Decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_EVEN)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid money value {value!r}") from exc


def usage_qty(value: Decimal | int | str) -> Decimal:
    if isinstance(value, float):
        raise TypeError("float is not allowed for usage quantities; use Decimal or str")
    try:
        quantized = Decimal(value).quantize(USAGE_QUANTUM, rounding=ROUND_HALF_EVEN)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid usage quantity {value!r}") from exc
    if quantized < ZERO:
        raise ValueError("usage quantity cannot be negative")
    return quantized


def display(value: Decimal) -> str:
    return str(money(value).quantize(DISPLAY_QUANTUM, rounding=ROUND_HALF_EVEN))


def is_zero(value: Decimal | int | str) -> bool:
    return money(value) == ZERO


def sum_money(values: list[Decimal]) -> Decimal:
    total = ZERO
    for value in values:
        total = money(total + money(value))
    return total
