# ElevenLabs Payments — Requirement-to-Evidence Matrix

**Audit date:** 2026-10-29  
**GitHub account:** [Kozphy](https://github.com/Kozphy) (authenticated as Kozphy via `gh`)  
**Target role:** [Full-Stack Engineer (Backend Leaning) — Payments](https://jobs.ashbyhq.com/elevenlabs/e4e0450f-d139-4f8e-b210-2f326a680d90)  
**Method:** Source inspection of local clones and shallow clones of private repos. Public mirrors inspected where noted.  
**Scope rule:** Status reflects implemented code and tests, not README ambition.

Access note: Priority private repos were accessible (`finops-cloud-cost-platform`, `global-commerce-data-platform`, `Market-Data-Platform-for-Analytics-Execution`, `tax-control-intelligence-platform`, `NovaPay-Intelligence-B2B-SaaS-`, `Windows-Network-Recovery-Toolkit`). Public repos also inspected. No fabricated production metrics.

## Status legend

| Status | Meaning |
| --- | --- |
| VERIFIED | Behavior exists in source and is backed by tests or an executable demo path |
| PARTIAL | Related code exists but missing money-grade correctness, scale, or payment semantics |
| DOCUMENTED_ONLY | Described in README/docs without matching implementation |
| MISSING | Not found in inspected repos |
| NOT_ASSESSED | Repo not relevant enough to deep-read for this requirement |

## Matrix

| Requirement | Repository | Source file | Evidence | Status | Gap | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| Python backend / production-style APIs | `finops-cloud-cost-platform` | `src/finops_platform/control/api.py`, `api.py` | FastAPI control API; Decimal string inputs; CI on GitHub Actions | VERIFIED | Demo auth (`X-Actor`); README states not production-safe RBAC | P2 |
| Python backend / APIs | `global-commerce-data-platform` | `src/api/main.py` | FastAPI over DuckDB gold warehouse | VERIFIED | Analytics API, not billing API; amounts as `float` in schemas | P2 |
| Python backend / APIs | `tax-control-intelligence-platform` | `backend/app/main.py` | FastAPI tax/control MVP | VERIFIED | SQLite demo; float money | P3 |
| Python backend / APIs | `ai-outbound-engine` (local, not on GitHub yet) | `backend/app/main.py` | FastAPI multi-tenant SaaS MVP | PARTIAL | Local only; mock ESP; not published | P1 |
| Accurate usage metering without latency tax | `usage-billing-engine` (local) | `backend/app/services/metering.py`, `outbox.py` | Idempotent `event_id` ingest + outbox → monthly aggregates; pytest | VERIFIED (local) | Not published; Redis worker optional (sync outbox default) | P0 |
| Usage-based pricing / subscriptions / invoices | `usage-billing-engine` (local) | `services/pricing.py`, `invoicing.py`, tests | Versioned plans, tiered rates, invoice generate + charge/refund | VERIFIED (local) | Mock provider; not on GitHub yet | P0 |
| Usage-based pricing / subscriptions / invoices | `NovaPay-Intelligence-B2B-SaaS-` | `components/checkout-modal.tsx`, README | Mock checkout UI; pricing cards; explicit “no real payment” | PARTIAL | Frontend prototype only; no invoice ledger | P1 |
| Usage-based pricing / invoices | `finops-cloud-cost-platform` | `control/ap_ar.py`, `control/tax.py`, honesty matrix | Synthetic AP/AR invoices; tax labeled stub | PARTIAL | Cloud-cost + GL demo, not customer usage billing | P1 |
| Reliable event processing / high-throughput pipelines | `Market-Data-Platform-for-Analytics-Execution` | `streaming/pipeline.py`, `storage/postgres.py`, SQL PK + `ON CONFLICT` | Polling pipeline, retries on PG connect, idempotent upserts | PARTIAL | Market ticks not billing events; uses `float`/`DOUBLE PRECISION`; not Kafka/streams at scale | P1 |
| Reliable event processing | `global-commerce-data-platform` | `pipeline/state.py`, `tests/test_incremental.py` | Watermarks; idempotent rerun; fail does not advance watermark; mart reconciles to facts | VERIFIED | Batch ETL; late/out-of-order events explicitly limited; unit_price as float | P1 |
| Payment provider + checkout | `usage-billing-engine` (local) | `services/payments.py`, `webhooks.py` | Mock charge/refund + idempotency; webhook dedupe; Stripe stub | PARTIAL | Live Stripe test-mode not enabled | P0 |
| Payment provider + checkout | `NovaPay-Intelligence-B2B-SaaS-` | README + checkout modal | Client-side mock only; card digits never leave browser | PARTIAL | No Stripe/webhook/backend | P0 |
| Payment provider + checkout | `ai-outbound-engine` | `services/email_provider.py` | Provider adapter pattern (email, not payments) | PARTIAL | Shows adapter/idempotency pattern transferable to payments | P2 |
| Enterprise billing migrations / backwards compatibility | `usage-billing-engine` (local) | `shadow_compare`, `PricingVersion` | Dual-calc shadow invoice delta without mutating live invoice | VERIFIED (local) | Not a full feature-flag rollout platform | P0 |
| Enterprise billing migrations / backwards compatibility | `finops-cloud-cost-platform` | `tests/integration/test_migrations.py` | Migration apply + idempotent re-apply tests | PARTIAL | Schema migrations ≠ pricing-version / shadow-billing migration | P1 |
| Finance / tax / reconciliation / audit | `finops-cloud-cost-platform` | `control/money.py`, `journal.py`, `reconciliation.py`, `audit.py`, `close.py` | Decimal money (float rejected); journals; recon; hash-chain audit; period close; AI cannot post | VERIFIED | Synthetic data; unauthenticated demo API | P1 |
| Finance / tax / reconciliation | `tax-control-intelligence-platform` | `reconciliation.py`, `validation_rules.py`, `constants.py` | Invoice–GL variance; duplicate rules; JSONL evidence | PARTIAL | `float` amounts + `AMOUNT_TOLERANCE = 0.01`; not Decimal ledger | P2 |
| Finance / reporting | `financial-data-automation` (public) | `validation.py`, `reporting.py`, `evidence.py` | Financial file pipeline + append-only audit evidence | PARTIAL | Report automation, not billing | P3 |
| Debug complex billing via logs/traces/code | `finops-cloud-cost-platform` | observability/metrics modules + correlation IDs in demos | Correlation IDs in closed-loop/close demos | PARTIAL | No OpenTelemetry traces or billing incident runbook verified in this pass | P2 |
| Debug / reliability tooling | `ci-failure-orchestrator` (public) | README | CI failure orchestration, retries, audit of self-heal | PARTIAL | Ops reliability, not money path | P3 |
| Debug / reliability | `franklin-mt-service` (public) | CorrelationId middleware, k8s manifests | Correlation IDs, retries, rate limit, health, K8s | VERIFIED (for reliability patterns; C# not Python billing) | Different domain/language | P2 |
| Strong automated testing | `finops-cloud-cost-platform` | `tests/`, `.github/workflows/ci.yml` | Unit + integration (Postgres isolation, migrations, workflows); ruff/mypy/secret scan | VERIFIED | Need billing-specific concurrency/idempotency suite | P1 |
| Strong automated testing | `global-commerce-data-platform` | `tests/test_incremental.py` etc. | Idempotent rerun, watermark, quality tests + CI | VERIFIED | Small synthetic volumes | P2 |
| Strong automated testing | `Market-Data-Platform-for-Analytics-Execution` | `tests/` | Streaming/cleaning/features/backtest tests | PARTIAL | No CI workflow in tree (no `.github` in local clone) | P2 |
| Security fundamentals | `finops-cloud-cost-platform` | CI secret_scan, pip_audit advisory; honesty matrix | Scans present; API auth weak by design | PARTIAL | Tenant isolation for billing customers not the product model | P1 |
| Security / tenant isolation | `ai-outbound-engine` | `tests/test_mvp_flow.py` | Cross-tenant ICP 404 test; JWT membership | VERIFIED | Not published; mock send | P1 |
| Cloud infra / DBs / Kubernetes | `franklin-mt-service` | `infra/k8s/*`, docker-compose | K8s deploy/service/scaling manifests | VERIFIED | C# service | P2 |
| Cloud infra / DBs | `Market-Data-Platform-for-Analytics-Execution` | docker-compose, Postgres, Airflow | Compose stack with Postgres + Airflow | VERIFIED | Local portfolio stack | P2 |
| Cloud infra / DBs | `finops-cloud-cost-platform` | docker-compose, SQL migrations, CI Postgres | Postgres-backed integration tests | VERIFIED | — | P2 |
| Safe deploy / observability / rollback | `franklin-mt-service` | Azure Pipelines + health endpoints | Deploy artifacts present | PARTIAL | Rollback runbook not verified this pass | P2 |
| Safe deploy / observability | `finops-cloud-cost-platform` | CI concurrency, migration tests | Migration safety tested | PARTIAL | No shadow pricing / feature-flag billing rollout | P0 |
| Decimal / no float money | `finops-cloud-cost-platform` | `control/money.py` | `TypeError` on float; ROUND_HALF_EVEN quantum | VERIFIED | Strongest money correctness in portfolio | P0 keep |
| Decimal / no float money | `global-commerce-data-platform` | `src/api/main.py` schemas | `unit_price`/`gross_sales` as float | MISSING (for money-grade) | Must not become billing source of truth without Decimal rewrite | P0 |
| Decimal / no float money | `tax-control-intelligence-platform` | `reconciliation.py` | float variance | MISSING (for money-grade) | Convert or isolate from billing engine | P1 |
| Idempotent persistence | `global-commerce-data-platform` | warehouse upserts + incremental tests | Rerun does not duplicate facts | VERIFIED | Not event-ID at-least-once billing | P1 |
| Idempotent persistence | `Market-Data-Platform-for-Analytics-Execution` | Postgres `ON CONFLICT` upsert | Natural key upsert | VERIFIED | Market keys ≠ usage event_id | P1 |
| Idempotent send/webhook pattern | `ai-outbound-engine` | `outbound_messages` unique `(org, idempotency_key)` | Send replay returns same message | VERIFIED | Email domain; transferable | P1 |
| Stripe sandbox + signed webhooks | `usage-billing-engine` (local) | `payments.verify_stripe_signature`, webhook ingest | Signature helper + event dedupe verified with mock provider | PARTIAL | No live Stripe sandbox keys exercised | P0 |
| 100k event benchmark with recorded metrics | `usage-billing-engine` (local) | `benchmarks/latest.json` | 100k events stored+outbox drained; machine-local SQLite smoke | VERIFIED (local smoke) | Not a multi-node/p99 production claim; not pushed | P1 |
| Windows-Network-Recovery-Toolkit | WNRT | various | Ops/diagnostics platform; embeds unrelated platform_core fragments | NOT_ASSESSED (low relevance) | Do not lead ElevenLabs application with this | P3 |

## Ranked repository relevance (ElevenLabs Payments)

| Rank | Repository | Visibility | Relevance | Why |
| --- | --- | --- | --- | --- |
| 0 | `usage-billing-engine` | Local only | Highest (JD-shaped) | Meter→price→invoice→payment/webhook; Decimal; tests; not pushed |
| 1 | `finops-cloud-cost-platform` | Private (+ public docs mirror) | Highest | Decimal ledger, recon, audit, migrations, CI, finance controls |
| 2 | `global-commerce-data-platform` | Private | High (pipeline) | Incremental idempotent ETL + FastAPI; needs Decimal + usage semantics |
| 3 | `Market-Data-Platform-for-Analytics-Execution` | Private | High (events) | Postgres upserts, retries, streaming loop, Airflow |
| 4 | `tax-control-intelligence-platform` | Private | Medium | Invoice/GL recon + audit evidence; float money weakens claim |
| 5 | `franklin-mt-service` | Public | Medium (infra) | K8s, correlation IDs, retries — supporting reliability story |
| 6 | `NovaPay-Intelligence-B2B-SaaS-` | Private | Low–Medium (UI only) | Checkout UX mock; honest disclaimer; no backend payments |
| 7 | `financial-data-automation` | Public | Medium-low | Validation/audit reporting hygiene |
| 8 | `ci-failure-orchestrator` | Public | Supporting | Reliability/CI narrative |
| 9 | `Windows-Network-Recovery-Toolkit` | Private | Low for this JD | Ops toolkit; not payments |
| — | `ai-outbound-engine` | Local only | High if published | Tenant isolation + idempotent provider pattern; not yet on GitHub |

## Architecture decision (before coding)

**Neither FinOps nor Commerce alone is a complete usage-billing engine.**

- FinOps is the right home for **Decimal money, journals, reconciliation, audit, migrations**.
- Commerce/Market-Data show **idempotent ingestion and pipelines**, but float pricing and non-billing domains.
- NovaPay is **UI only**.

**Recommendation for Phase 3+:** create a focused standalone `usage-billing-engine` that owns metering → pricing → invoice → payment adapter, and **import or share patterns** from FinOps (`money.py` invariants) rather than bolting a full Stripe stack into FinOps cloud-cost allocation. Extending FinOps in-place would blur FinOps vs customer-billing product boundaries and risk float leakage from FOCUS/pandas paths.

Ownership boundaries:

| Capability | Owner |
| --- | --- |
| Decimal money + GL-style controls | FinOps control plane (reuse patterns) |
| Usage event ingest + ledger + invoices + Stripe adapter | `usage-billing-engine` (new) |
| High-throughput upsert / watermark lessons | Commerce + Market-Data (reference, don’t fork business logic) |
| Checkout UX | NovaPay or thin React in billing engine |
| Tax rule demos | Tax platform (advisory; not legal authority) |

## Top gaps for ElevenLabs (ranked) — post Phase 3+

1. **Publish** `usage-billing-engine` (still local).  
2. **Stripe test-mode** end-to-end (adapter stubbed; mock path verified).  
3. **Recorded 100k benchmark** on disk (`benchmarks/latest.json`).  
4. **Public portfolio** still does not surface strongest private FinOps evidence.  
5. **Float money** in Commerce/Tax must not be presented as billing-grade.

## What this audit did not do

- Did not change product code.  
- Did not push, merge, or alter visibility.  
- Did not run full FinOps/Commerce test suites in this pass (CI presence and source/tests inspected).  
- Did not claim production ElevenLabs-scale throughput.
