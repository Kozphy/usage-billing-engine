# Evidence report

## Implemented

- Durable usage ingest with content-hash conflicts (409)
- Outbox worker, retries, crash reclaim, explicit replay
- Versioned pricing, inclusive UTC periods, Decimal money
- Immutable finalized invoices + late adjustments
- Mock payments + Stripe adapter code (test-mode when key present)
- Webhook signature verification + dedupe
- Shadow compare classification + cutover/rollback
- Structured JSON logs + correlation IDs
- JWT tenant isolation
- Incorrect-bill period-boundary regression
- Docker Compose: Postgres + API + worker
- CI: ruff + pytest with Postgres service

## Executed and verified (this workspace)

Commands:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
ruff check app tests
python ../scripts/migration_rehearsal.py
```

**Results recorded 2026-10-30 (this machine):**

| Check | Result |
|---|---|
| `pytest -m "not postgres"` | 22 passed |
| `pytest -m postgres` against Compose Postgres `:5433` | 2 passed |
| `ruff check app tests` | clean |
| `scripts/migration_rehearsal.py` | blocked unexpected delta → cutover with expected_delta → rollback; invoice total unchanged (`benchmarks/migration_rehearsal.json`) |

Postgres concurrency tests require `TEST_DATABASE_URL` (Compose DB on `localhost:5433` or CI service).

Benchmark (optional, machine-local):

```bash
python scripts/benchmark_100k.py 100000
# → benchmarks/latest.json
```

Prior recorded local smoke (`benchmarks/latest.json`, SQLite, 2026-10-29):

| Metric | Value |
|---|---|
| Events | 100000 |
| Ingest seconds | 113.902 |
| Outbox seconds | 58.403 |
| Ingest EPS | 877.94 |
| End-to-end EPS | 580.36 |
| Hardware note | Developer laptop; **not** a production SLA |

Re-run on your machine before citing numbers. Do not extrapolate.

Migration rehearsal:

```bash
python scripts/migration_rehearsal.py
# → benchmarks/migration_rehearsal.json
```

## Simulated / unverified

| Item | State |
|---|---|
| Stripe test-mode PaymentIntents | Code present; **not executed** without `STRIPE_SECRET_KEY` |
| Stripe hosted Checkout UI | Not implemented (PaymentIntent test PM path only) |
| Production traffic / on-call | Not claimed |
| Tax calculations | Extension point returns 0 |
| Multi-region durability | Not claimed |

## Related portfolio patterns (read-only reuse)

- Decimal helpers inspired by `Kozphy/finops-cloud-cost-platform` money control patterns
- Evidence/docs style informed by EvalForge / ci-failure-orchestrator portfolio repos
