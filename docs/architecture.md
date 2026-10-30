# Architecture

```
Client / meter
    │  (at-least-once)
    ▼
FastAPI + JWT tenant + correlation ID
    │
    ├─► UsageEvent  (uq org+event_id, content_hash, received_at, schema_version)
    │         │
    │         ▼  same DB transaction
    │    OutboxMessage (pending)
    │         │
    │         ▼  durable worker (FOR UPDATE SKIP LOCKED)
    │    UsageAggregate (recomputed; replay-safe)
    │
    ├─ PricingPlan / PricingVersion / PricingComponent
    │
    ├─ Invoice + InvoiceLine (immutable after finalize)
    │         └─ InvoiceAdjustment (late usage; does not rewrite totals)
    │
    ├─ PaymentAttempt (idempotency_key) → Mock | Stripe test-mode
    ├─ WebhookEvent (provider event dedupe + signature check)
    ├─ ShadowInvoice (classification + cutover gate)
    └─ PricingCutover / AuditLog
```

## Why this durable design

For portfolio scope, a **transactional outbox in Postgres** plus a small worker beats Kafka/Celery:

- Ingest and outbox enqueue commit together → no “acked but lost” window.
- Workers claim with `SKIP LOCKED` → concurrent drain without double apply.
- Aggregates are recomputed from events → at-least-once outbox is safe.
- Terminal failures are visible (`failed` + `last_error`) and replay is explicit.

## Non-goals

- Kubernetes, Kafka, multi-provider orchestration, large frontend
- Real tax engines, FX, card storage
- Production Stripe claims without keys/evidence
