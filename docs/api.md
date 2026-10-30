# API map

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/register` | — | Create org + user |
| POST | `/auth/login` | — | OAuth2 password → JWT |
| POST | `/customers` | JWT | Create customer |
| POST | `/metrics` | JWT | Create billable metric |
| POST | `/plans` | JWT | Create plan + v1 |
| POST | `/plans/{code}/versions` | JWT | Append pricing version |
| POST | `/subscriptions` | JWT | Attach customer to plan version |
| POST | `/usage/events` | JWT | Ingest one event |
| POST | `/usage/events:batch` | JWT | Batch ingest |
| POST | `/invoices/generate` | JWT | Build invoice for period |
| POST | `/invoices/{id}/charge` | JWT | Charge via payment adapter |
| POST | `/invoices/{id}/refund` | JWT | Refund paid invoice |
| POST | `/invoices/shadow-compare` | JWT | Alternate pricing delta |
| POST | `/webhooks/{provider}?organization_id=` | signature optional | Provider callbacks |
| GET | `/reports/summary` | JWT | Rollup |
| POST | `/ops/outbox/process` | JWT | Drain pending outbox |
| GET | `/health` | — | Liveness |

Quantity and money fields in JSON should be **strings** (e.g. `"0.0100"`) to avoid float parsing.
