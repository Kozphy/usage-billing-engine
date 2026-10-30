from datetime import datetime, timezone
from decimal import Decimal


def test_webhook_idempotency_and_shadow(client, auth_headers):
    headers, org_id = auth_headers
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
            "event_id": "w1",
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
    charge = client.post(
        f"/invoices/{inv['id']}/charge",
        headers=headers,
        json={"idempotency_key": "wh-pay"},
    ).json()

    payload = {
        "id": "evt_wh_1",
        "type": "invoice.paid",
        "provider_payment_id": charge["provider_payment_id"],
        "invoice_id": inv["id"],
    }
    wh1 = client.post(f"/webhooks/mock?organization_id={org_id}", json=payload)
    wh2 = client.post(f"/webhooks/mock?organization_id={org_id}", json=payload)
    assert wh1.status_code == 200
    assert wh2.status_code == 200
    assert wh1.json()["duplicate"] is False
    assert wh2.json()["duplicate"] is True

    # New pricing version at higher rate for shadow compare
    v2 = client.post(
        "/plans/api/versions",
        headers=headers,
        json={
            "base_fee": "0",
            "components": [
                {"metric_code": "api_calls", "model": "flat_per_unit", "unit_price": "0.2000"}
            ],
        },
    )
    assert v2.status_code == 200, v2.text
    shadow = client.post(
        "/invoices/shadow-compare",
        headers=headers,
        json={
            "invoice_id": inv["id"],
            "alternate_pricing_version_id": v2.json()["id"],
        },
    )
    assert shadow.status_code == 200, shadow.text
    assert Decimal(shadow.json()["total"]) == Decimal("2.0000")
    assert Decimal(shadow.json()["delta"]) == Decimal("1.0000")

    summary = client.get("/reports/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["invoices_paid"] >= 1
