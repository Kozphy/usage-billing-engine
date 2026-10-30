# ElevenLabs Payments Engineering — requirements → evidence

| Role theme | Project evidence | Status |
|---|---|---|
| Accurate usage metering | Idempotent ingest, content-hash conflicts, `received_at`/`occurred_at`, Postgres unique + concurrency tests | Implemented + verified (local/CI) |
| Customer billing | Versioned prices, UTC inclusive periods, Decimal invoices, line→event traceability | Implemented + verified |
| Payment-provider integration | Mock adapter (deterministic); Stripe test-mode code path via PaymentIntents + signature verify | Mock verified; **Stripe live test-mode unverified** without keys |
| Reliable event processing | Transactional outbox, worker, SKIP LOCKED, bounded retries, crash reclaim, safe replay | Implemented + verified (unit; PG claim in compose) |
| Safe pricing migrations | Shadow classify, cutover gate, rollback, rehearsal script | Implemented + verified |
| Debug incorrect bills | Case study + period-boundary regression test | Documented + verified |
| Security / isolation | JWT org scoping, admin ops behind auth, webhook signatures, secrets via env | Implemented + verified in tests |
| Observability | Structured JSON logs, `X-Correlation-ID` event→outbox→invoice→payment | Implemented |
| Performance evidence | `scripts/benchmark_100k.py` + `benchmarks/latest.json` | Measured locally (see evidence); machine-specific |

## Still needs real operational experience (not claimed)

- Production on-call for payment incidents
- Real Stripe production traffic / disputes / chargebacks
- Multi-region failover and multi-year ledger migrations
- Tax engine certification
- SOC2 / PCI scope ownership (this project stores no card PANs)
