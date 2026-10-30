import hashlib
import hmac
import json
import time

from app.services.payments import verify_stripe_signature


def test_verify_stripe_signature_accepts_valid():
    secret = "whsec_test"
    payload = b'{"id":"evt_1","type":"invoice.paid"}'
    ts = str(int(time.time()))
    signed = f"{ts}.".encode() + payload
    sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    header = f"t={ts},v1={sig}"
    assert verify_stripe_signature(payload, header, secret) is True


def test_verify_stripe_signature_rejects_invalid():
    payload = b'{"id":"evt_1"}'
    assert verify_stripe_signature(payload, "t=1,v1=deadbeef", "whsec_test") is False


def test_stripe_webhook_invalid_signature_401(client, auth_headers):
    headers, org_id = auth_headers
    payload = {"id": "evt_bad", "type": "invoice.paid"}
    res = client.post(
        f"/webhooks/stripe?organization_id={org_id}",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json", "Stripe-Signature": "t=1,v1=nope"},
    )
    assert res.status_code == 401
