#!/usr/bin/env python3
"""Synthetic 100k usage ingest benchmark (local correctness + throughput smoke).

Writes results to benchmarks/latest.json. Not a competitive claim — measured on
whatever machine runs it. Uses in-process SQLite + sync outbox.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT / 'benchmarks' / 'bench.db'}")
# Defer outbox drain until after ingest for throughput smoke; still processes all messages.
os.environ.setdefault("OUTBOX_SYNC", "false")
os.environ.setdefault("PAYMENT_PROVIDER", "mock")
os.environ.setdefault("SECRET_KEY", "bench-secret")

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db import Base  # noqa: E402
from app.models import Organization, UsageEvent, User  # noqa: E402
from app.schemas import UsageEventIn  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import metering  # noqa: E402
from app.models import Customer, Metric  # noqa: E402


def main(n: int = 100_000) -> None:
    out_dir = ROOT / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "bench.db"
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, future=True)
    db = Session()

    org = Organization(name="Bench Org")
    db.add(org)
    db.flush()
    db.add(
        User(
            organization_id=org.id,
            email="bench@example.com",
            hashed_password=hash_password("password123"),
        )
    )
    customer = Customer(
        organization_id=org.id,
        name="Bench Customer",
        external_ref="bench-cust",
    )
    metric = Metric(
        organization_id=org.id,
        code="units",
        name="Units",
        unit="unit",
    )
    db.add_all([customer, metric])
    db.commit()

    from app.services.outbox import process_pending
    from sqlalchemy import func

    started = time.perf_counter()
    batch = 1000
    for i in range(n):
        event = UsageEventIn(
            event_id=f"bench-{i}-{uuid.uuid4().hex[:8]}",
            customer_external_ref="bench-cust",
            metric_code="units",
            quantity="1",
            occurred_at=datetime(2026, 3, 15, tzinfo=timezone.utc),
        )
        metering.ingest_event(db, organization_id=org.id, event=event)
        if (i + 1) % batch == 0:
            db.commit()
            print(f"ingested {i + 1}/{n}", flush=True)
    db.commit()
    ingest_elapsed = time.perf_counter() - started

    outbox_started = time.perf_counter()
    drained = 0
    while True:
        nproc = process_pending(db, limit=5000)
        db.commit()
        drained += nproc
        if nproc == 0:
            break
    outbox_elapsed = time.perf_counter() - outbox_started
    elapsed = ingest_elapsed + outbox_elapsed

    count = db.scalar(
        select(func.count()).select_from(UsageEvent).where(UsageEvent.organization_id == org.id)
    )

    result = {
        "events_requested": n,
        "events_stored": count,
        "outbox_drained": drained,
        "ingest_seconds": round(ingest_elapsed, 3),
        "outbox_seconds": round(outbox_elapsed, 3),
        "elapsed_seconds": round(elapsed, 3),
        "events_per_second_ingest": round(n / ingest_elapsed, 2) if ingest_elapsed else None,
        "events_per_second_end_to_end": round(n / elapsed, 2) if elapsed else None,
        "database": "sqlite",
        "outbox_sync": False,
        "note": "Local smoke benchmark; not a production SLA claim.",
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }
    path = out_dir / "latest.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    db.close()


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    main(n)
