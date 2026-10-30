# Evidence-bounded résumé bullets

Use only what this repo actually demonstrates:

1. Built a Python/FastAPI usage-billing service with Decimal money, idempotent event ingest (including conflict detection), and PostgreSQL uniqueness constraints proven under concurrent duplicate submissions.

2. Implemented a transactional outbox + durable worker with bounded retries, crash recovery, and an explicit late-usage adjustment policy that keeps finalized invoices immutable.

3. Added shadow pricing comparison with expected/unexpected delta classification, cutover blocking, and rollback that retargets subscriptions without rewriting finalized invoices or replaying payment charges.
