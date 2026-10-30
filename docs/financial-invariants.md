# Financial invariants and delivery semantics

## Money and rounding

Floats are rejected at API and helper boundaries (`TypeError`). All arithmetic uses `Decimal`.

`ROUND_HALF_EVEN` (banker's rounding) stays the only rounding mode. It is unbiased across a book of invoices, and this service already used it for the storage grid. There is no reason to switch to half-up.

### Two scales

| Scale | Where | Quantum |
|---|---|---|
| Storage / catalog | `money()`, unit prices, base fees, `Numeric(20, 4)` columns | `0.0001` |
| Usage quantity | `usage_qty()` | `0.000001` |
| Invoice line, display, provider amount | `invoice_amount` / `round_money` / `to_minor_units` | ISO 4217 minor unit of the invoice currency |

Catalog rates are quantized to `0.0001` when a plan is saved, because that is the column scale. That save-time step is not an invoice round.

### Round once per invoice line

`price_quantity` multiplies catalog rates by usage at full `Decimal` precision. It does **not** round each tier band or the running total.

Each invoice line (base fee and each usage component) is then rounded **once** to the currency minor unit. The invoice `subtotal` is the exact sum of those posted lines. `tax_total` is posted on the same grid (always zero in this build). `total` is `subtotal + tax_total`, so:

`invoice.total == sum(line.amount for line in invoice.lines) + invoice.tax_total`

with tax at zero, the total equals the sum of the rounded lines.

Rounding each band to the minor unit and then summing can differ by a cent (or a fraction of a cent on the storage grid) from rounding the exact extension once. The posted line uses the single round. `sum_money` adds exact `Decimal` values and does not quantize each step.

Tiered `unit_price` on a line is an informational average at storage precision. The charge is `line.amount`, not `unit_price * quantity`.

### Currency minor units

`app/currencies.py` maps ISO 4217 alphabetic codes to minor-unit exponents (SIX List One scale, not processor overrides):

| Code | Exponent | Minor units per 1 major unit |
|---|---|---|
| USD | 2 | 100 |
| TWD | 2 | 100 (ISO; not a zero-decimal override) |
| JPY | 0 | 1 |
| KWD | 3 | 1000 |

Examples that follow ISO where some processors differ: ISK and CLP are 0; IDR, CVE, and HUF are 2.

Unknown codes, including codes with no defined exponent (`XAU`, `XAG`, `XPT`, `XPD`, `XDR`), raise `UnknownCurrencyError`. Customer and plan create reject them. Invoice generation also rejects a plan currency that does not match the customer currency. This service does not convert FX; prices are interpreted in the customer currency.

The largest exponent in the table is 4 (`CLF`, `UYW`), so a currency-rounded amount always fits `Numeric(20, 4)`. Posted amounts are stored at that scale with trailing zeros. No schema migration is required. A future currency with more than four decimal places would need a migration before it could be posted.

Display formatting (`display`) uses the currency exponent: USD and TWD two places, JPY none, KWD three.

### Provider charges

`payment_attempts.amount` stores the major-unit posted total (same number as the invoice). The value **sent** to the provider is an integer number of minor units (`to_minor_units`): USD 10.00 → `1000`, JPY 500 → `500`, KWD 1.234 → `1234`, TWD 10.50 → `1050`. Refund requests that are not already on the currency minor unit are rejected rather than silently re-rounded.

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
2. An `InvoiceAdjustment` is created for that event's exact extension, rounded once to the invoice currency.
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
