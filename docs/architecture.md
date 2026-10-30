# Architecture

```
Client / meter
    │
    ▼
FastAPI (JWT tenant) ──► UsageEvent (idempotent event_id)
    │                         │
    │                         ▼
    │                    OutboxMessage (usage.ingested)
    │                         │
    │                         ▼
    │                    UsageAggregate (calendar month)
    │
    ├── PricingPlan / PricingVersion / PricingComponent
    │         (flat_per_unit | tiered)
    │
    ├── Invoice + InvoiceLine  ◄── sum events × versioned rates + base_fee
    │
    ├── PaymentAttempt (idempotency_key) → Mock | Stripe stub
    ├── Refund
    ├── WebhookEvent (provider event dedupe)
    └── ShadowInvoice (alternate version delta)
```

## Money

All accounting amounts go through `money()` / `usage_qty()`. Floats raise `TypeError` at the boundary.

## Reliability patterns

| Pattern | Implementation |
|---|---|
| Idempotent ingest | Unique `(org, event_id)` |
| Transactional outbox | `outbox_messages` + sync drain (`OUTBOX_SYNC=true`) |
| Payment idempotency | Unique `(org, idempotency_key)` |
| Webhook replay safety | Unique `(org, provider, provider_event_id)` |
| Pricing migration rehearsal | `shadow_invoices` compare without mutating live invoice |
| Audit | Append-only `audit_logs` |

## Non-goals (this MVP)

- Real Stripe Settlement / Tax / Entitlements UI
- Multi-currency FX
- Distributed Celery workers (Redis present for future; sync outbox used now)
