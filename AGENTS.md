# Agent instructions — usage-billing-engine

## Purpose

Portfolio payments/billing service for demonstrating metering, invoicing, outbox reliability, and safe pricing migrations. Prefer financial correctness over feature count.

## Hard constraints

- Do not invent production customers, SLAs, or Stripe verification without keys/evidence.
- Do not push, publish, deploy, or change repo visibility unless the user explicitly asks.
- Never commit secrets or print credentials.
- Prefer Decimal money; reject floats.
- Finalized invoices are immutable; late usage → adjustments.
- Do not claim end-to-end exactly-once delivery.

## Layout

- `backend/app` — FastAPI service, worker, domain services
- `backend/tests` — unit (SQLite) + `postgres` marked integration tests
- `docs/` — architecture, invariants, runbooks, evidence, interview demo
- `scripts/` — benchmark + migration rehearsal
- `docker-compose.yml` — Postgres, Redis, API, worker

## Verification

```bash
cd backend && pip install -e ".[dev]" && pytest -q && ruff check app tests
```

## Cloud Agent

The saved environment installs the Python 3.12 dev tools and PostgreSQL 16. It does not configure Stripe.

- `pytest`, `ruff`, `uvicorn`, and `alembic` are on `PATH` from `~/.local/billing-venv`.
- PostgreSQL listens on `127.0.0.1:5433`. The role, password, and database are `billing`, matching the default URL in `backend/tests/conftest.py`. `pytest -q` runs the postgres-marked tests when that server is up.
- On boot, Postgres starts and the API listens on `0.0.0.0:8000` using SQLite (`backend/billing.db`) and the mock payment provider. Health is `GET /health`. OpenAPI is `/docs`.

## Patterns reused (do not modify those repos from here)

- FinOps Decimal money discipline
- Evidence-bounded documentation
