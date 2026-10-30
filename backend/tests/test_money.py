from decimal import Decimal

import pytest

from app.money import display, money, sum_money, usage_qty


def test_rejects_float_money():
    with pytest.raises(TypeError):
        money(0.1)  # type: ignore[arg-type]


def test_rejects_float_usage():
    with pytest.raises(TypeError):
        usage_qty(1.5)  # type: ignore[arg-type]


def test_bankers_rounding():
    assert money("0.12345") == Decimal("0.1234")
    assert money("0.12355") == Decimal("0.1236")


def test_sum_and_display():
    assert sum_money([Decimal("0.1000"), Decimal("0.2000")]) == Decimal("0.3000")
    assert display(Decimal("1.2")) == "1.20"


def test_sum_money_does_not_quantize_each_step():
    # Each addend is exactly halfway to 0.0000 on the storage grid (even digit).
    # Rounding each step would collapse the sum to zero.
    parts = [Decimal("0.00005"), Decimal("0.00005"), Decimal("0.00005")]
    assert money(parts[0]) == Decimal("0.0000")
    assert sum_money(parts) == Decimal("0.00015")
