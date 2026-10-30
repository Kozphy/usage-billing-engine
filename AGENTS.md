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

## Patterns reused (do not modify those repos from here)

- FinOps Decimal money discipline
- Evidence-bounded documentation
