from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models import PricingComponent
from app.money import money
from app.services.pricing import price_quantity


@given(
    qty=st.decimals(min_value=0, max_value=1_000_000, places=6, allow_nan=False, allow_infinity=False),
    unit=st.decimals(min_value=0, max_value=100, places=4, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=50)
def test_flat_price_non_negative_and_linear(qty, unit):
    component = PricingComponent(
        pricing_version_id="x",
        metric_id="m",
        model="flat_per_unit",
        unit_price=money(unit),
        tiers_json=None,
    )
    _avg, amount = price_quantity(component, Decimal(qty))
    assert amount >= 0
    assert amount == money(money(unit) * Decimal(qty))
