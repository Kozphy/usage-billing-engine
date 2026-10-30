"""Currency minor units and single-round invoice lines."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import parse_qs

import httpx
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.config import get_settings
from app.currencies import MINOR_UNITS
from app.models import Invoice, PricingComponent
from app.money import (
    UnknownCurrencyError,
    display,
    invoice_amount,
    minor_unit_places,
    money,
    round_money,
    sum_money,
    to_minor_units,
)
from app.services.payments import MockPaymentProvider, StripeAdapter, minor_unit_charge
from app.services.pricing import price_quantity


def _tiered(tiers: list[dict]) -> PricingComponent:
    return PricingComponent(
        pricing_version_id="x",
        metric_id="m",
        model="tiered",
        unit_price=Decimal("0"),
        tiers_json=json.dumps(tiers),
    )


def test_iso_minor_units_and_unknown_codes():
    assert minor_unit_places("usd") == 2
    assert minor_unit_places("TWD") == 2
    assert minor_unit_places("JPY") == 0
    assert minor_unit_places("KWD") == 3
    # ISO exponents, including cases some processors override.
    assert minor_unit_places("ISK") == 0
    assert minor_unit_places("CLP") == 0
    assert minor_unit_places("IDR") == 2
    assert minor_unit_places("CVE") == 2
    assert minor_unit_places("HUF") == 2
    assert max(MINOR_UNITS.values()) <= 4
    for code in ("XXX", "US", "XAU", "XDR"):
        with pytest.raises(UnknownCurrencyError):
            round_money("1", code)
        with pytest.raises(UnknownCurrencyError):
            to_minor_units("1", code)


@pytest.mark.parametrize(
    ("currency", "amount", "posted", "minor", "shown"),
    [
        ("USD", "10.00", "10.0000", 1000, "10.00"),
        ("USD", "10.235", "10.2400", 1024, "10.24"),
        ("USD", "1.015", "1.0200", 102, "1.02"),
        ("USD", "1.005", "1.0000", 100, "1.00"),
        ("JPY", "500", "500.0000", 500, "500"),
        ("JPY", "11.5", "12.0000", 12, "12"),
        ("JPY", "10.5", "10.0000", 10, "10"),
        ("KWD", "1.2345", "1.2340", 1234, "1.234"),
        ("KWD", "1.2335", "1.2340", 1234, "1.234"),
        ("KWD", "1.0005", "1.0000", 1000, "1.000"),
        ("TWD", "10.50", "10.5000", 1050, "10.50"),
        ("TWD", "10.235", "10.2400", 1024, "10.24"),
    ],
)
def test_currency_rounding_and_minor_units(currency, amount, posted, minor, shown):
    assert invoice_amount(amount, currency) == Decimal(posted)
    assert round_money(amount, currency) == Decimal(shown)
    assert to_minor_units(amount, currency) == minor
    assert display(amount, currency) == shown
    # Posted storage scale does not change the minor-unit value.
    assert to_minor_units(invoice_amount(amount, currency), currency) == minor


def test_tier_extension_is_not_rounded_per_band():
    """Three half-units at 0.0001: per-band storage rounding drops the charge."""
    component = _tiered(
        [
            {"up_to": "0.5", "unit_price": "0.0001"},
            {"up_to": "1.0", "unit_price": "0.0001"},
            {"up_to": None, "unit_price": "0.0001"},
        ]
    )
    _avg, exact = price_quantity(component, Decimal("1.5"))
    assert exact == Decimal("0.00015")
    legacy = Decimal("0")
    band = Decimal("0.0001") * Decimal("0.5")
    for _ in range(3):
        legacy = money(legacy + money(band))
    assert legacy == Decimal("0")
    assert exact != legacy
    assert money(exact) == Decimal("0.0002")


def test_multi_tier_usd_line_rounds_once():
    """0.014 three times is 0.042 → 0.04 USD, not 0.01 + 0.01 + 0.01."""
    component = _tiered(
        [
            {"up_to": "1", "unit_price": "0.0140"},
            {"up_to": "2", "unit_price": "0.0140"},
            {"up_to": None, "unit_price": "0.0140"},
        ]
    )
    _avg, exact = price_quantity(component, Decimal("3"))
    assert exact == Decimal("0.042")
    posted = invoice_amount(exact, "USD")
    per_band = sum((invoice_amount(Decimal("0.0140"), "USD") for _ in range(3)), Decimal("0"))
    assert posted == Decimal("0.0400")
    assert per_band == Decimal("0.0300")
    assert posted != per_band


def test_minor_unit_charge_is_not_hardcoded_cents():
    jpy_minor, jpy = minor_unit_charge(Decimal("500"), "jpy")
    kwd_minor, kwd = minor_unit_charge(Decimal("1.234"), "KWD")
    twd_minor, twd = minor_unit_charge(Decimal("10.50"), "TWD")
    usd_minor, usd = minor_unit_charge(Decimal("10.00"), "USD")
    assert (jpy_minor, jpy) == (500, "JPY")
    assert (kwd_minor, kwd) == (1234, "KWD")
    assert (twd_minor, twd) == (1050, "TWD")
    assert (usd_minor, usd) == (1000, "USD")
    # The previous adapter multiplied every currency by 100.
    assert jpy_minor != 500 * 100
    assert kwd_minor != int(Decimal("1.234") * 100)


def test_mock_and_stripe_send_minor_units(monkeypatch):
    invoice = Invoice(id="inv-currency-1", currency="KWD")
    mock = MockPaymentProvider().charge(
        invoice=invoice,
        amount=Decimal("1.2345"),
        currency="KWD",
        idempotency_key="k" * 16,
    )
    assert mock["amount_minor"] == 1234
    assert mock["amount"] == "1234"
    assert mock["currency"] == "KWD"

    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    get_settings.cache_clear()
    captured: dict[str, str] = {}

    class _Resp:
        status_code = 200
        text = ""

        def json(self) -> dict:
            return {"id": "pi_test", "status": "succeeded"}

    def _post(url, content=None, headers=None, timeout=None):  # noqa: ANN001
        captured["url"] = url
        captured["content"] = content.decode() if isinstance(content, bytes) else content
        return _Resp()

    monkeypatch.setattr(httpx, "post", _post)
    # StripeAdapter looks up httpx on its module, which imported the name.
    monkeypatch.setattr("app.services.payments.httpx.post", _post)
    try:
        result = StripeAdapter().charge(
            invoice=invoice,
            amount=Decimal("1.2345"),
            currency="KWD",
            idempotency_key="idem-kwd",
        )
    finally:
        get_settings.cache_clear()

    parsed = parse_qs(captured["content"])
    assert parsed["amount"] == ["1234"]
    assert parsed["currency"] == ["kwd"]
    assert result["amount_minor"] == 1234

    refund_invoice = Invoice(id="inv-currency-1", currency="JPY", provider_invoice_id="pi_test")
    captured.clear()
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    get_settings.cache_clear()
    try:
        refund = StripeAdapter().refund(invoice=refund_invoice, amount=Decimal("500"), reason="goodwill")
    finally:
        get_settings.cache_clear()
    parsed = parse_qs(captured["content"])
    assert parsed["amount"] == ["500"]
    assert refund["amount_minor"] == 500


@given(
    raw_lines=st.lists(
        st.decimals(
            min_value=0,
            max_value=10_000,
            places=6,
            allow_nan=False,
            allow_infinity=False,
        ),
        min_size=1,
        max_size=12,
    ),
    currency=st.sampled_from(["USD", "JPY", "KWD", "TWD"]),
)
@settings(max_examples=40)
def test_total_equals_sum_of_rounded_lines(raw_lines, currency):
    posted = [invoice_amount(line, currency) for line in raw_lines]
    tax = invoice_amount(0, currency)
    total = sum_money([*posted, tax])
    assert total == sum(posted, Decimal("0"))
    assert total == invoice_amount(total, currency)


@given(
    q1=st.integers(min_value=1, max_value=400),
    q2=st.integers(min_value=0, max_value=400),
    p1=st.decimals(min_value=0, max_value=20, places=4, allow_nan=False, allow_infinity=False),
    p2=st.decimals(min_value=0, max_value=20, places=4, allow_nan=False, allow_infinity=False),
    currency=st.sampled_from(["USD", "JPY", "KWD", "TWD"]),
)
@settings(max_examples=30)
def test_tiered_property_rounds_the_line_once(q1, q2, p1, p2, currency):
    component = _tiered(
        [
            {"up_to": str(q1), "unit_price": str(money(p1))},
            {"up_to": None, "unit_price": str(money(p2))},
        ]
    )
    _avg, exact = price_quantity(component, Decimal(q1 + q2))
    expected = money(p1) * Decimal(q1) + money(p2) * Decimal(q2)
    assert exact == expected
    assert invoice_amount(exact, currency) == invoice_amount(expected, currency)


def _seed_currency(client, headers, *, currency: str, unit_price: str, model: str, tiers=None):
    customer = client.post(
        "/customers",
        headers=headers,
        json={"name": "Acme", "external_ref": f"acme-{currency}", "currency": currency},
    )
    assert customer.status_code == 200, customer.text
    customer_body = customer.json()
    assert customer_body["currency"] == currency
    metric_code = f"units-{currency.lower()}"
    metric = client.post(
        "/metrics",
        headers=headers,
        json={"code": metric_code, "name": f"Units {currency}", "unit": "unit"},
    )
    assert metric.status_code == 200, metric.text
    component = {"metric_code": metric_code, "model": model, "unit_price": unit_price}
    if tiers is not None:
        component["tiers"] = tiers
    plan = client.post(
        "/plans",
        headers=headers,
        json={
            "code": f"plan-{currency}",
            "name": currency,
            "currency": currency,
            "base_fee": "0.0140" if currency == "USD" else "0",
            "components": [component],
        },
    )
    assert plan.status_code == 200, plan.text
    sub = client.post(
        "/subscriptions",
        headers=headers,
        json={"customer_id": customer_body["id"], "plan_code": f"plan-{currency}"},
    )
    assert sub.status_code == 200, sub.text
    return customer_body


def test_invoice_total_matches_rounded_lines(client, auth_headers):
    headers, _ = auth_headers
    customer = _seed_currency(
        client,
        headers,
        currency="USD",
        unit_price="0",
        model="tiered",
        tiers=[
            {"up_to": "1", "unit_price": "0.0140"},
            {"up_to": "2", "unit_price": "0.0140"},
            {"up_to": None, "unit_price": "0.0140"},
        ],
    )
    ingested = client.post(
        "/usage/events",
        headers=headers,
        json={
            "event_id": "usd-drift",
            "customer_external_ref": "acme-USD",
            "metric_code": "units-usd",
            "quantity": "3",
            "occurred_at": datetime(2026, 5, 2, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert ingested.status_code == 200, ingested.text
    inv = client.post(
        "/invoices/generate",
        headers=headers,
        json={
            "customer_id": customer["id"],
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
        },
    )
    assert inv.status_code == 200, inv.text
    body = inv.json()
    lines = [Decimal(line["amount"]) for line in body["lines"]]
    # Base 0.014 → 0.01 and usage 0.042 → 0.04. Per-band usage rounding would be 0.03.
    assert Decimal("0.0400") in lines
    assert Decimal("0.0100") in lines
    assert Decimal(body["subtotal"]) == sum(lines, Decimal("0"))
    assert Decimal(body["total"]) == Decimal(body["subtotal"]) + Decimal(body["tax_total"])
    assert Decimal(body["tax_total"]) == Decimal("0")
    assert Decimal(body["total"]) == Decimal("0.0500")

    bad_refund_setup = client.post(
        f"/invoices/{body['id']}/charge",
        headers=headers,
        json={"idempotency_key": "usd-drift-pay"},
    )
    assert bad_refund_setup.status_code == 200, bad_refund_setup.text
    off_grid = client.post(
        f"/invoices/{body['id']}/refund",
        headers=headers,
        json={"amount": "0.001", "reason": "not a cent"},
    )
    assert off_grid.status_code == 400


def test_jpy_and_kwd_invoice_lines(client, auth_headers):
    headers, _ = auth_headers
    jpy = _seed_currency(client, headers, currency="JPY", unit_price="11.5000", model="flat_per_unit")
    kwd = _seed_currency(client, headers, currency="KWD", unit_price="1.2345", model="flat_per_unit")
    for customer, ref, quantity, expected in (
        (jpy, "acme-JPY", "1", Decimal("12.0000")),
        (kwd, "acme-KWD", "1", Decimal("1.2340")),
    ):
        ingested = client.post(
            "/usage/events",
            headers=headers,
            json={
                "event_id": f"evt-{ref}",
                "customer_external_ref": ref,
                "metric_code": f"units-{customer['currency'].lower()}",
                "quantity": quantity,
                "occurred_at": datetime(2026, 6, 2, tzinfo=timezone.utc).isoformat(),
            },
        )
        assert ingested.status_code == 200, ingested.text
        inv = client.post(
            "/invoices/generate",
            headers=headers,
            json={
                "customer_id": customer["id"],
                "period_start": "2026-06-01",
                "period_end": "2026-06-30",
            },
        )
        assert inv.status_code == 200, inv.text
        body = inv.json()
        lines = [Decimal(line["amount"]) for line in body["lines"]]
        assert Decimal(body["total"]) == expected
        assert Decimal(body["total"]) == sum(lines, Decimal("0"))
        assert body["currency"] == customer["currency"]


def test_unknown_currency_and_mismatch_rejected(client, auth_headers):
    headers, _ = auth_headers
    unknown = client.post(
        "/customers",
        headers=headers,
        json={"name": "Nope", "external_ref": "nope", "currency": "XYZ"},
    )
    assert unknown.status_code == 422
    customer = client.post(
        "/customers",
        headers=headers,
        json={"name": "Yen", "external_ref": "yen", "currency": "jpy"},
    )
    assert customer.status_code == 200
    assert customer.json()["currency"] == "JPY"
    client.post(
        "/metrics",
        headers=headers,
        json={"code": "units", "name": "Units", "unit": "unit"},
    )
    plan = client.post(
        "/plans",
        headers=headers,
        json={
            "code": "usd-plan",
            "name": "USD",
            "currency": "USD",
            "base_fee": "0",
            "components": [
                {"metric_code": "units", "model": "flat_per_unit", "unit_price": "1.0000"}
            ],
        },
    )
    assert plan.status_code == 200, plan.text
    mismatched = client.post(
        "/subscriptions",
        headers=headers,
        json={"customer_id": customer.json()["id"], "plan_code": "usd-plan"},
    )
    assert mismatched.status_code == 400
