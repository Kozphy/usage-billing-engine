# Evidence

## Verified (automated)

- `tests/test_money.py` — float rejection, Decimal rounding
- `tests/test_metering_idempotency.py` — duplicate `event_id`
- `tests/test_pricing_invoice.py` — tiered invoice math + charge idempotency + refund
- `tests/test_webhooks_shadow.py` — webhook dedupe + shadow delta
- `tests/test_pricing_properties.py` — Hypothesis flat pricing linearity

## Mock / stub

- `MockPaymentProvider` — default local charges
- `StripeAdapter` — raises unless/until live keys + intentional enablement
- Webhook Stripe signature helper exists; live Stripe payloads not exercised in CI

## Benchmark

- `scripts/benchmark_100k.py` produces `benchmarks/latest.json`
- Treat numbers as **machine-local smoke**, not a published SLA
- Recorded local run (2026-10-29): see `benchmarks/latest.json` (SQLite; not production SLA)

## Related portfolio evidence

- FinOps Decimal patterns: `finops-cloud-cost-platform/src/finops_platform/control/money.py`
- Prior audit: `artifacts/elevenlabs-payments-audit/`
