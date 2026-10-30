# Usage Billing Engine

Portfolio-grade **usage metering → versioned pricing → invoices → payment adapter → webhooks** service.

Built to align with payments / FinOps interview themes (usage-based billing, Decimal money, idempotent ingest, outbox, shadow pricing migrations). **Mock payment provider by default** — Stripe adapter is stubbed until real keys exist.

## Status

| Capability | State |
|---|---|
| Decimal money (no float) | Verified in tests |
| Idempotent usage ingest (`event_id`) | Verified |
| Outbox → monthly aggregates | Verified (sync mode) |
| Versioned pricing + tiered rates | Verified |
| Invoice generation | Verified |
| Mock charge / refund + idempotency keys | Verified |
| Webhook dedupe | Verified |
| Shadow pricing compare | Verified |
| Stripe live charges | Stub only (`PAYMENT_PROVIDER=stripe` raises) |
| 100k ingest benchmark | Script ready (`scripts/benchmark_100k.py`) — run locally; results are machine-specific |

## Quick start

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Optional Compose (Postgres + Redis + API):

```bash
docker compose up --build
```

## Demo flow

1. `POST /auth/register` → Bearer token  
2. Create customer, metric, plan (flat or tiered), subscription  
3. `POST /usage/events` with string quantities (`"1500"`, not floats)  
4. `POST /invoices/generate`  
5. `POST /invoices/{id}/charge` with `idempotency_key`  
6. Optional: `POST /invoices/shadow-compare` against a new pricing version  

OpenAPI: `http://localhost:8000/docs`

## Tests

```bash
cd backend
pytest -q
```

## Benchmark (optional)

```bash
python scripts/benchmark_100k.py 100000
# writes benchmarks/latest.json — not a production SLA claim
```

## Design notes

- Money helpers mirror FinOps Decimal patterns (`app/money.py`).
- Usage uniqueness: `(organization_id, event_id)`.
- Webhook uniqueness: `(organization_id, provider, provider_event_id)`.
- Payment uniqueness: `(organization_id, idempotency_key)`.
- Multi-tenant isolation via JWT `org` claim on authenticated routes.

## Docs

- [Architecture](docs/architecture.md)
- [API map](docs/api.md)
- [Evidence / verification](docs/evidence.md)

## Constraints

- No secrets committed. No live Stripe without keys.  
- Not published / pushed unless you explicitly approve.  
