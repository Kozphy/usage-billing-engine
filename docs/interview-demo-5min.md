# Five-minute interview demonstration

Goal: show financial correctness under failure, not feature tourism.

| Time | Action | Talking point |
|---|---|---|
| 0:00–0:40 | Open `docs/architecture.md` + health | Small system: FastAPI, Postgres, outbox worker. USD + one usage unit. |
| 0:40–1:30 | Ingest same `event_id` twice; then conflict payload | Persist-before-ack; identical retry idempotent; different content → 409. Not exactly-once E2E. |
| 1:30–2:20 | Generate invoice; show line → `source_event_ids` + pricing version | Traceability event → invoice line → price version. Decimal money. |
| 2:20–3:10 | Charge with repeated idempotency key; optional webhook replay | Payment status separate from calculation; webhook dedupe. |
| 3:10–4:10 | Late event after finalize; show adjustment, unchanged total | Explicit late policy; immutability. |
| 4:10–4:50 | Shadow compare unexpected → cutover 409; declare expected_delta → cutover + rollback | Safe pricing migration with gate. |
| 4:50–5:00 | Point at `docs/evidence.md` + pytest/CI | What was measured vs simulated (Stripe test-mode unverified without keys). |

Commands (local SQLite/dev):

```bash
cd backend && pip install -e ".[dev]" && pytest -q
# or: docker compose up --build
```
