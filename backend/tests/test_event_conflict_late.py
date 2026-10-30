from datetime import datetime, timezone
from decimal import Decimal


def _seed(client, headers):
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
    client.post(
        "/plans",
        headers=headers,
        json={
            "code": "voice",
            "name": "Voice",
            "base_fee": "0",
            "components": [
                {"metric_code": "tts_chars", "model": "flat_per_unit", "unit_price": "0.0100"}
            ],
        },
    )
    client.post(
        "/subscriptions",
        headers=headers,
        json={"customer_id": customer["id"], "plan_code": "voice"},
    )
    return customer


def test_conflicting_event_id_returns_409(client, auth_headers):
    headers, _ = auth_headers
    _seed(client, headers)
    base = {
        "event_id": "same-id",
        "customer_external_ref": "acme-1",
        "metric_code": "tts_chars",
        "quantity": "100",
        "occurred_at": datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
        "schema_version": 1,
    }
    assert client.post("/usage/events", headers=headers, json=base).status_code == 200
    conflict = client.post(
        "/usage/events",
        headers=headers,
        json={**base, "quantity": "999"},
    )
    assert conflict.status_code == 409
    assert "conflict" in conflict.json()["detail"].lower() or "different" in conflict.json()["detail"]


def test_late_usage_creates_adjustment_without_mutating_invoice(client, auth_headers):
    headers, _ = auth_headers
    customer = _seed(client, headers)
    client.post(
        "/usage/events",
        headers=headers,
        json={
            "event_id": "early",
            "customer_external_ref": "acme-1",
            "metric_code": "tts_chars",
            "quantity": "100",
            "occurred_at": datetime(2026, 3, 5, tzinfo=timezone.utc).isoformat(),
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
    assert Decimal(inv["total"]) == Decimal("1.0000")
    total_before = inv["total"]

    late = client.post(
        "/usage/events",
        headers=headers,
        json={
            "event_id": "late-1",
            "customer_external_ref": "acme-1",
            "metric_code": "tts_chars",
            "quantity": "50",
            "occurred_at": datetime(2026, 3, 20, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert late.status_code == 200
    assert late.json()["status"] == "late"

    again = client.get(f"/invoices/{inv['id']}", headers=headers).json()
    assert again["total"] == total_before
    assert len(again["adjustments"]) == 1
    assert Decimal(again["adjustments"][0]["amount"]) == Decimal("0.5000")


def test_duplicate_invoice_generation_is_idempotent(client, auth_headers):
    headers, _ = auth_headers
    customer = _seed(client, headers)
    client.post(
        "/usage/events",
        headers=headers,
        json={
            "event_id": "idem-inv",
            "customer_external_ref": "acme-1",
            "metric_code": "tts_chars",
            "quantity": "10",
            "occurred_at": datetime(2026, 3, 1, tzinfo=timezone.utc).isoformat(),
        },
    )
    body = {
        "customer_id": customer["id"],
        "period_start": "2026-03-01",
        "period_end": "2026-03-31",
    }
    a = client.post("/invoices/generate", headers=headers, json=body).json()
    b = client.post("/invoices/generate", headers=headers, json=body).json()
    assert a["id"] == b["id"]
    assert a["total"] == b["total"]


def test_tenant_isolation_on_invoice_get(client, auth_headers):
    headers_a, _ = auth_headers
    customer = _seed(client, headers_a)
    client.post(
        "/usage/events",
        headers=headers_a,
        json={
            "event_id": "iso-1",
            "customer_external_ref": "acme-1",
            "metric_code": "tts_chars",
            "quantity": "10",
            "occurred_at": datetime(2026, 3, 1, tzinfo=timezone.utc).isoformat(),
        },
    )
    inv = client.post(
        "/invoices/generate",
        headers=headers_a,
        json={
            "customer_id": customer["id"],
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
        },
    ).json()

    other = client.post(
        "/auth/register",
        json={
            "organization_name": "Other Org",
            "email": "other@example.com",
            "password": "password123",
        },
    ).json()
    headers_b = {"Authorization": f"Bearer {other['access_token']}"}
    denied = client.get(f"/invoices/{inv['id']}", headers=headers_b)
    assert denied.status_code == 404
