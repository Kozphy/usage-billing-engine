# Financial invariants and delivery semantics

## Money

- All posted amounts use `Decimal` via `money()` / `usage_qty()`.
- Floats are rejected at API and helper boundaries (`TypeError`).
- Money quantum: `0.0001` with `ROUND_HALF_EVEN` (banker's rounding).
- Usage quantum: `0.000001`.
- Display formatting uses two places; posted values keep four.

## Usage ingestion delivery semantics

| Guarantee | Meaning in this system |
|---|---|
| Persist-before-ack | Row is flushed (unique constraint applied) before HTTP 200 |
| Idempotent identical retry | Same `(organization_id, event_id)` + same content hash → 200 + `duplicate=true` |
| Conflict on reuse | Same `event_id`, different billable content → **409** |
| Concurrent duplicates | Unique constraint + savepoint retry → one winner; no double bill |
| Not exactly-once E2E | Clients may retry; outbox may redeliver; handlers are idempotent |

**Do not claim end-to-end exactly-once.** Claim: *at-least-once delivery with idempotent financial effects*.

## Event time vs receive time

- `occurred_at` — client event time (timezone-aware; stored UTC). Drives billing period.
- `received_at` — server clock at accept time. Used for ops/latency, **not** period assignment.
- Out-of-order arrivals are accepted; aggregates key off `occurred_at`.

## Late usage policy

If an **open / paid / finalized** invoice already covers the event's UTC date:

1. Event is stored with `status=late`.
2. An `InvoiceAdjustment` is created for the priced amount under the invoice's pricing version.
3. Finalized invoice `subtotal` / `total` are **never rewritten**.

Adjustments settle operationally as debit/credit memos (next cycle or admin review) — they are not silent invoice edits.

## Billing periods

- Default demo periods are UTC calendar month inclusive bounds: `[period_start, period_end]`.
- Invoice generation sums events with `occurred_at::date` in that closed interval.
- Regenerating the same `(org, customer, period)` returns the existing immutable invoice.

## Invoices and payments

- Finalization sets `finalized_at` and status `open`. Line items become immutable.
- `tax_total` is always `0` in this build (`app/services/tax.py` extension point).
- Payment attempts are a separate ledger (`payment_attempts`) keyed by idempotency key.
- Paying an invoice updates payment status; it does not recalculate lines.

## Pricing migration

- Shadow compare runs legacy vs alternate calculator on **frozen** usage for an invoice period.
- Classifications: `match` | `expected_delta` | `unexpected_delta`.
- Cutover is blocked unless every listed invoice's latest shadow allows cutover.
- Cutover only retargets **active subscriptions** forward; finalized invoices and payments are untouched.
- Rollback restores prior subscription version pointers.
