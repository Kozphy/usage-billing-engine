# Pricing migration and rollback runbook

## Preconditions

- Frozen usage for the rehearsal invoices (no concurrent ingest into those periods, or accept late-adjustment policy).
- New `PricingVersion` created via `POST /plans/{code}/versions`.
- Operator authenticated with org JWT.

## Rehearsal steps

```bash
# 1) Shadow compare each finalized invoice against the candidate version
curl -s -X POST "$API/invoices/shadow-compare" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"invoice_id\":\"$INV\",\"alternate_pricing_version_id\":\"$V2\",\"expected_delta\":\"1.0000\"}"

# classification must be match or expected_delta; cutover_allowed=true

# 2) Cutover (blocked with 409 if any unexpected_delta)
curl -s -X POST "$API/pricing/cutover" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"plan_code\":\"api\",\"to_pricing_version_id\":\"$V2\",\"invoice_ids\":[\"$INV\"]}"

# 3) Verify active subscriptions now point at V2 (GET catalog / DB)

# 4) Rollback if needed
curl -s -X POST "$API/pricing/cutover/$CUTOVER_ID/rollback" \
  -H "Authorization: Bearer $TOKEN"
```

Automated rehearsal script: `scripts/migration_rehearsal.py` (writes `benchmarks/migration_rehearsal.json`).

## What cutover does **not** do

- Rewrite finalized invoice totals
- Re-charge or duplicate payment attempts
- Delete shadow rows (audit trail retained)

## Rollback criteria

- Unexpected production traffic on new rates
- Shadow misses discovered after cutover
- Payment provider anomalies unrelated to pricing math (investigate separately; do not “fix” by rewriting invoices)
