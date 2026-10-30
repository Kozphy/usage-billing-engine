# Portfolio narrative (ElevenLabs Payments alignment)

This repo closes the P0 gap called out in the ElevenLabs payments audit: a **standalone usage billing engine** rather than bolting Stripe onto FinOps or treating commerce float prices as ledger-grade.

## JD themes → artifacts

| Theme | Where to look |
|---|---|
| Usage metering | `app/services/metering.py`, unique `event_id` |
| Usage-based / tiered pricing | `app/services/pricing.py`, versioned plans |
| Invoicing | `app/services/invoicing.py` |
| Payment provider adapter | `app/services/payments.py` (mock verified; Stripe stub) |
| Webhooks + replay safety | `app/services/webhooks.py` |
| Migrations / shadow | `shadow_compare` + `ShadowInvoice` |
| Audit | `app/services/audit.py` |
| Reliability | outbox, idempotency keys, Decimal money |
| Scale smoke | `scripts/benchmark_100k.py` |

## Honesty boundary

Do not claim production Stripe volume, customer revenue, or competitive benchmarks. Claim: **correctness-first billing skeleton with verified Decimal/idempotency behavior**.
