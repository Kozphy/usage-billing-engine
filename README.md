# Usage Billing Engine

Focused portfolio service: **usage metering → versioned pricing → immutable invoices → payment adapter → safe pricing migration**.

Built for payments-engineering interview themes (Decimal money, idempotent ingest, outbox recovery, late-usage adjustments, shadow cutover). Synthetic customers only. **Mock payment provider by default.**

## Status

| Capability | State |
|---|---|
| Decimal money (no float) | Verified |
| Idempotent ingest + content-hash conflict (409) | Verified |
| Durable outbox worker + bounded retries + crash reclaim | Verified |
| Inclusive UTC periods + late adjustments | Verified |
| Versioned pricing + invoice line traceability | Verified |
| Mock charge / refund + idempotency keys | Verified |
| Webhook dedupe + signature reject | Verified |
| Shadow classify + cutover gate + rollback | Verified |
| Postgres uniqueness / concurrency tests | Verified when Postgres available / CI |
| Stripe test-mode | Code path present; **unverified without keys** |
| 100k ingest benchmark | Script + local JSON; machine-specific |

## Quick start

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Compose (Postgres + API + durable worker; `OUTBOX_SYNC=false`):

```bash
docker compose up --build
```

## Demo flow

1. `POST /auth/register` → Bearer token  
2. Create customer, metric (`tts_chars` or `api_calls`), plan, subscription  
3. `POST /usage/events` with string quantities and timezone-aware `occurred_at`  
4. `POST /invoices/generate`  
5. `POST /invoices/{id}/charge` with `idempotency_key`  
6. Optional late event → adjustment without total rewrite  
7. Optional `POST /invoices/shadow-compare` then `/pricing/cutover`

OpenAPI: `http://localhost:8000/docs`

## Tests

```bash
cd backend
pytest -q
ruff check app tests
```

Postgres integration (optional local):

```bash
docker compose up -d db
# Windows PowerShell:
$env:TEST_DATABASE_URL="postgresql+psycopg://billing:billing@127.0.0.1:5433/billing"
pytest -q -m postgres
```

## Docs

- [Architecture](docs/architecture.md)
- [Financial invariants / delivery semantics](docs/financial-invariants.md)
- [Migration runbook](docs/migration-runbook.md)
- [Incorrect-bill case study](docs/incorrect-bill-case-study.md)
- [Evidence report](docs/evidence.md)
- [5-minute interview demo](docs/interview-demo-5min.md)
- [Requirements → evidence](docs/requirements-to-evidence.md)
- [Résumé bullets](docs/resume-bullets.md)

## Constraints

- No secrets committed. No live Stripe claims without keys + recorded evidence.  
- Do not publish/push/deploy unless explicitly requested.  
- Not end-to-end exactly-once — at-least-once with idempotent effects.
