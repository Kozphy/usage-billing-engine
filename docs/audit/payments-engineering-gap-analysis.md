# Payments engineering gap analysis

## Executive verdict

You already have **credible finance-control and data-pipeline engineering** in private repos. As of Phase 3+ (2026-10-29), a local **`usage-billing-engine`** now covers meter → price → invoice → mock payment/webhook → shadow compare with Decimal money and pytest proof. Stripe live mode and a recorded 100k benchmark artifact remain optional follow-ups; the repo is **not pushed** yet.

## Strengths to keep

1. **FinOps `control/money.py`**: rejects `float`, Decimal quantum, banker's rounding — rare and on-message for payments.
2. **FinOps control plane**: journals, SoD approval, reconciliation, period close, hash-chained audit, AI advisory that cannot post.
3. **Commerce incremental ETL**: watermark only advances on success; idempotent reruns tested.
4. **Market-Data Postgres upserts** with natural keys + connection retry.
5. **Honest READMEs** (NovaPay, FinOps honesty matrix) — protect interview credibility.

## Critical gaps (P0) — updated after Phase 3+

| Gap | Why ElevenLabs cares | Status after Phase 3+ |
| --- | --- | --- |
| Usage event ledger | Core of the JD | **CLOSED locally** — `usage-billing-engine` idempotent `event_id` |
| Stripe test mode + webhooks | Checkout + provider work | **PARTIAL** — mock webhooks + signature helper; Stripe charge stub |
| Versioned pricing | Enterprise migration theme | **CLOSED locally** — `PricingVersion` on invoices |
| Shadow / migration demo | JD: extend/replace without disruption | **CLOSED locally** — `shadow_compare` |
| Benchmark evidence | Prove pipeline seriousness | **CLOSED locally (smoke)** — `benchmarks/latest.json` (SQLite; not SLA) |

## Important gaps (P1)

- Publish or selectively open-source FinOps control excerpts so the public portfolio matches private strength (`finops-cloud-cost-platform-public` is docs-only today).
- Replace float money in any path marketed as billing.
- Add OpenTelemetry + billing incident runbook.
- Put `ai-outbound-engine` on GitHub only after cleaning secrets and clarifying it is CRM/outbound, not payments — or extract the idempotency/tenant patterns into the billing engine.

## What not to do

- Do not claim NovaPay processes payments.
- Do not merge billing into FinOps FOCUS allocation code (domain collision + float risk from analytics frames).
- Do not inflate Market-Data polling into “Kafka stream processing at scale.”
- Do not run or claim 100k benchmarks until results are on disk.

## Next implementation order

1. ~~Scaffold `usage-billing-engine`~~ done.  
2. ~~Event ingest + outbox + idempotent metering~~ done (sync outbox).  
3. ~~Pricing + invoices~~ done.  
4. ~~Mock payment + webhook dedupe~~ done; Stripe live still stub.  
5. ~~Correctness tests + 100k local smoke~~ done (`benchmarks/latest.json`).  
6. Portfolio publish / GitHub push — **awaiting approval**.  
7. Optional: Stripe test-mode keys, OTel, K8s manifests.
