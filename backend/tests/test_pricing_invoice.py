from datetime import datetime, timezone
from decimal import Decimal


def _bootstrap(client, headers):
    customer = client.post(
        "/customers",
        headers=headers,
        json={"name": "Acme", "external_ref": "acme-1"},
    ).json()
    client.post(
        "/metrics",
        headers=headers,
        json={"code": "tts_chars", "name": "TTS Characters", "unit": "char"},
    )
    plan = client.post(
        "/plans",
        headers=headers,
        json={
            "code": "voice-usage",
            "name": "Voice Usage",
            "base_fee": "10.0000",
            "components": [
                {
                    "metric_code": "tts_chars",
                    "model": "tiered",
                    "unit_price": "0",
                    "tiers": [
                        {"up_to": "1000", "unit_price": "0.0100"},
                        {"up_to": None, "unit_price": "0.0080"},
                    ],
                }
            ],
        },
    )
    assert plan.status_code == 200, plan.text
    sub = client.post(
        "/subscriptions",
        headers=headers,
        json={"customer_id": customer["id"], "plan_code": "voice-usage"},
    )
    assert sub.status_code == 200, sub.text
    return customer, plan.json(), sub.json()


def test_invoice_math_tiered(client, auth_headers):
    headers, _ = auth_headers
    customer, _plan, _sub = _bootstrap(client, headers)
    # 1500 chars: 1000 @ 0.01 + 500 @ 0.008 = 10 + 4 = 14 usage + 10 base = 24
    client.post(
        "/usage/events",
        headers=headers,
        json={
            "event_id": "u1",
            "customer_external_ref": "acme-1",
            "metric_code": "tts_chars",
            "quantity": "1500",
            "occurred_at": datetime(2026, 3, 10, tzinfo=timezone.utc).isoformat(),
        },
    )
    inv = client.post(
        "/invoices/generate",
        headers=headers,
        json={
            "customer_id": customer["id"],
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
        },
    )
    assert inv.status_code == 200, inv.text
    body = inv.json()
    assert Decimal(body["total"]) == Decimal("24.0000")
    assert body["status"] == "open"


def test_charge_idempotent_and_refund(client, auth_headers):
    headers, _ = auth_headers
    customer, _plan, _sub = _bootstrap(client, headers)
    client.post(
        "/usage/events",
        headers=headers,
        json={
            "event_id": "u2",
            "customer_external_ref": "acme-1",
            "metric_code": "tts_chars",
            "quantity": "100",
            "occurred_at": datetime(2026, 3, 11, tzinfo=timezone.utc).isoformat(),
        },
    )
    inv = client.post(
        "/invoices/generate",
        headers=headers,
        json={
            "customer_id": customer["id"],
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
        },
    ).json()
    charge1 = client.post(
        f"/invoices/{inv['id']}/charge",
        headers=headers,
        json={"idempotency_key": "pay-1"},
    )
    charge2 = client.post(
        f"/invoices/{inv['id']}/charge",
        headers=headers,
        json={"idempotency_key": "pay-1"},
    )
    assert charge1.status_code == 200
    assert charge2.status_code == 200
    assert charge1.json()["id"] == charge2.json()["id"]
    assert charge1.json()["status"] == "succeeded"
    refund = client.post(
        f"/invoices/{inv['id']}/refund",
        headers=headers,
        json={"amount": "1.0000", "reason": "goodwill"},
    )
    assert refund.status_code == 200, refund.text
