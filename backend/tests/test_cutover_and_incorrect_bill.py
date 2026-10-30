"""Pricing cutover gate + incorrect-bill regression (period boundary bug)."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import sessionmaker

from app.models import Customer, Metric, Organization, UsageEvent
from app.money import money
from app.services.metering import sum_usage


def _bootstrap_api(client, headers):
    customer = client.post(
        "/customers",
        headers=headers,
        json={"name": "Acme", "external_ref": "acme-1"},
    ).json()
    client.post(
        "/metrics",
        headers=headers,
        json={"code": "api_calls", "name": "API Calls", "unit": "call"},
    )
    plan = client.post(
        "/plans",
        headers=headers,
        json={
            "code": "api",
            "name": "API",
            "base_fee": "0",
            "components": [
                {"metric_code": "api_calls", "model": "flat_per_unit", "unit_price": "0.1000"}
            ],
        },
    ).json()
    client.post(
        "/subscriptions",
        headers=headers,
        json={"customer_id": customer["id"], "plan_code": "api"},
    )
    client.post(
        "/usage/events",
        headers=headers,
        json={
            "event_id": "c1",
            "customer_external_ref": "acme-1",
            "metric_code": "api_calls",
            "quantity": "10",
            "occurred_at": datetime(2026, 4, 1, tzinfo=timezone.utc).isoformat(),
        },
    )
    inv = client.post(
        "/invoices/generate",
        headers=headers,
        json={
            "customer_id": customer["id"],
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
    ).json()
    return customer, plan, inv


def test_cutover_blocked_on_unexpected_delta(client, auth_headers):
    headers, _ = auth_headers
    _customer, _plan, inv = _bootstrap_api(client, headers)
    v2 = client.post(
        "/plans/api/versions",
        headers=headers,
        json={
            "base_fee": "0",
            "components": [
                {"metric_code": "api_calls", "model": "flat_per_unit", "unit_price": "0.2000"}
            ],
        },
    ).json()
    shadow = client.post(
        "/invoices/shadow-compare",
        headers=headers,
        json={"invoice_id": inv["id"], "alternate_pricing_version_id": v2["id"]},
    ).json()
    assert shadow["classification"] == "unexpected_delta"
    assert shadow["cutover_allowed"] is False

    blocked = client.post(
        "/pricing/cutover",
        headers=headers,
        json={
            "plan_code": "api",
            "to_pricing_version_id": v2["id"],
            "invoice_ids": [inv["id"]],
        },
    )
    assert blocked.status_code == 409


def test_cutover_allowed_with_declared_expected_delta(client, auth_headers):
    headers, _ = auth_headers
    _customer, _plan, inv = _bootstrap_api(client, headers)
    v2 = client.post(
        "/plans/api/versions",
        headers=headers,
        json={
            "base_fee": "0",
            "components": [
                {"metric_code": "api_calls", "model": "flat_per_unit", "unit_price": "0.2000"}
            ],
        },
    ).json()
    shadow = client.post(
        "/invoices/shadow-compare",
        headers=headers,
        json={
            "invoice_id": inv["id"],
            "alternate_pricing_version_id": v2["id"],
            "expected_delta": "1.0000",
        },
    ).json()
    assert shadow["classification"] == "expected_delta"
    assert shadow["cutover_allowed"] is True

    ok = client.post(
        "/pricing/cutover",
        headers=headers,
        json={
            "plan_code": "api",
            "to_pricing_version_id": v2["id"],
            "invoice_ids": [inv["id"]],
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["action"] == "cutover"

    rb = client.post(f"/pricing/cutover/{ok.json()['id']}/rollback", headers=headers)
    assert rb.status_code == 200
    assert rb.json()["action"] == "rollback"


def _buggy_sum_usage_exclusive_end(events, period_start, period_end):
    """Historical bug: treated period_end as exclusive, dropping end-of-month usage."""
    total = Decimal("0")
    for occurred, qty in events:
        if period_start <= occurred < period_end:  # bug: should be <=
            total += qty
    return total


def test_incorrect_bill_period_boundary_regression(db_engine):
    """Case study: end-of-period event dropped by exclusive upper bound.

    Reproduce → root cause (exclusive period_end) → fix (inclusive) → regression.
    """
    events = [
        (date(2026, 3, 1), Decimal("10")),
        (date(2026, 3, 31), Decimal("5")),
    ]
    buggy = _buggy_sum_usage_exclusive_end(events, date(2026, 3, 1), date(2026, 3, 31))
    assert buggy == Decimal("10")  # incorrectly drops March 31

    Session = sessionmaker(bind=db_engine, future=True)
    db = Session()
    org = Organization(name="Boundary Org")
    db.add(org)
    db.flush()
    customer = Customer(organization_id=org.id, name="C", external_ref="c1")
    metric = Metric(organization_id=org.id, code="units", name="Units", unit="unit")
    db.add_all([customer, metric])
    db.flush()
    for i, (d, q) in enumerate(events):
        db.add(
            UsageEvent(
                organization_id=org.id,
                customer_id=customer.id,
                metric_id=metric.id,
                event_id=f"e{i}",
                quantity=q,
                occurred_at=datetime(d.year, d.month, d.day, tzinfo=timezone.utc),
                content_hash=f"h{i}",
                status="applied",
            )
        )
    db.commit()

    fixed = sum_usage(
        db,
        organization_id=org.id,
        customer_id=customer.id,
        metric_id=metric.id,
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
    )
    assert fixed == Decimal("15.000000")
    assert money(fixed * Decimal("0.0100")) == money("0.1500")
