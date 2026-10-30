# Incorrect-bill debugging case study

## Scenario

A customer disputed a March invoice that omitted usage on **2026-03-31**.

Synthetic setup:

| Field | Value |
|---|---|
| Customer | Boundary Org / `c1` |
| Metric | `units` |
| Events | 10 units on 2026-03-01; 5 units on 2026-03-31 |
| Period | 2026-03-01 … 2026-03-31 |
| Expected total qty | 15 |
| Buggy total qty | 10 |

## 1. Reproduce

```python
# Exclusive upper bound (the bug)
period_start <= occurred < period_end   # drops occurred == period_end
```

Regression harness: `tests/test_cutover_and_incorrect_bill.py::test_incorrect_bill_period_boundary_regression`.

## 2. Trace

1. **Logs** — structured JSON with `correlation_id` on ingest (`usage_ingested`).
2. **Database** — `usage_events` shows both rows with `status=applied` and correct `occurred_at`.
3. **Code** — invoice path calls `sum_usage()`; the bug lived in an exclusive end comparison.

## 3. Correct

Use inclusive bounds:

```python
period_start <= occurred_date <= period_end
```

Implemented in `app/services/metering.py::sum_usage`.

## 4. Verify

- Unit/regression test asserts qty `15.000000` for the March window.
- Property tests in `test_pricing_properties.py` continue to guard flat pricing linearity.
- No finalized invoices were rewritten; a corrected **new draft** would be issued only if the bad invoice were still draft. For already-finalized mistakes, policy is adjustment/credit — not silent rewrite.
