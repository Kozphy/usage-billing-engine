from datetime import datetime, timezone


def _seed(client, headers):
    c = client.post(
        "/customers",
        headers=headers,
        json={"name": "Acme", "external_ref": "acme-1"},
    )
    assert c.status_code == 200
    m = client.post(
        "/metrics",
        headers=headers,
        json={"code": "tts_chars", "name": "TTS Characters", "unit": "char"},
    )
    assert m.status_code == 200
    return c.json(), m.json()


def test_duplicate_event_id_is_idempotent(client, auth_headers):
    headers, _org = auth_headers
    _seed(client, headers)
    payload = {
        "event_id": "evt-1",
        "customer_external_ref": "acme-1",
        "metric_code": "tts_chars",
        "quantity": "1000",
        "occurred_at": datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
    }
    first = client.post("/usage/events", headers=headers, json=payload)
    second = client.post("/usage/events", headers=headers, json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert first.json()["id"] == second.json()["id"]


def test_batch_ingest(client, auth_headers):
    headers, _org = auth_headers
    _seed(client, headers)
    res = client.post(
        "/usage/events:batch",
        headers=headers,
        json={
            "events": [
                {
                    "event_id": f"b-{i}",
                    "customer_external_ref": "acme-1",
                    "metric_code": "tts_chars",
                    "quantity": "10",
                    "occurred_at": datetime(2026, 3, 2, tzinfo=timezone.utc).isoformat(),
                }
                for i in range(5)
            ]
        },
    )
    assert res.status_code == 200
    assert len(res.json()) == 5
