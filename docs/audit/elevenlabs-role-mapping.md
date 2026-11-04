# ElevenLabs role mapping (from public JD)

Source: [Ashby job posting](https://jobs.ashbyhq.com/elevenlabs/e4e0450f-d139-4f8e-b210-2f326a680d90) retrieved 2026-10-29.

## What the Payments team owns (JD)

Billing, usage tracking, pricing, and payments across self-serve and enterprise. Correctness is non-negotiable because it underpins revenue and is customer-visible.

## JD responsibilities → portfolio signal

| JD theme | Best current signal | Honesty |
| --- | --- | --- |
| Usage tracking without latency impact | Missing dedicated meter | Do not claim |
| Enterprise pricing/usage migration + stream processing | FinOps migrations + Market-Data/Commerce pipelines | Adjacent; not billing migration |
| Upgrade/pay / new payment providers | NovaPay mock UI | Explicitly non-payment |
| Finance/Tax compliance, audit, reporting | FinOps control + Tax platform | Synthetic demos |
| Growth/pricing experiments | Not found as experiment framework | Missing |
| Debug complex billing from UX + logs + code | Correlation IDs / audit chains | Partial |
| Collaborate across Sales/Finance/eng | Soft skill; not proven in code | N/A |

## Hard requirements (JD) → evidence

| Requirement | Portfolio |
| --- | --- |
| Expertise in Python | Strong (FinOps, Commerce, Market-Data, Tax, Outbound) |
| Backend development | Strong FastAPI presence |
| APIs, cloud tools, storage, data structures | Postgres, DuckDB, Docker, some K8s (Franklin) |
| Test design + security fundamentals | FinOps CI strong; auth often demo-grade |
| Care with live money systems | FinOps Decimal + AI-cannot-post is the best story |
| Learn large systems / debug production | Franklin + CI orchestrator support narrative |

## Bonus → evidence

| Bonus | Portfolio |
| --- | --- |
| Payment providers / usage-based billing | Weak (mock only) |
| Stream processing / high-throughput events | Medium (Market-Data polling + PG upserts; Commerce incremental) |
| Finance/tax/audit | Strong (FinOps + Tax) |
| Kubernetes | Franklin manifests |

## Application positioning (accurate)

Lead with **financial correctness + Python backend + idempotent data planes**, not with “I built Stripe.” State clearly that payment-provider integration and usage metering are the next build, grounded in FinOps Decimal invariants.
