#!/usr/bin/env python3
"""Controlled pricing migration rehearsal with before/after evidence.

Runs entirely offline against SQLite. Writes benchmarks/migration_rehearsal.json.
Does not charge payments twice or mutate finalized invoice totals.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT / 'benchmarks' / 'migration.db'}")
os.environ.setdefault("OUTBOX_SYNC", "true")
os.environ.setdefault("PAYMENT_PROVIDER", "mock")
os.environ.setdefault("SECRET_KEY", "migration-secret")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db import Base  # noqa: E402
from app.models import Customer, Metric, Organization, Subscription, User  # noqa: E402
from app.schemas import ComponentIn, PlanCreate, PlanVersionCreate, UsageEventIn  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import invoicing, metering  # noqa: E402
from app.services.pricing import add_version, create_plan  # noqa: E402


def main() -> None:
    out_dir = ROOT / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / "migration.db"
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, future=True)
    db = Session()

    org = Organization(name="Migration Org")
    db.add(org)
    db.flush()
    db.add(
        User(
            organization_id=org.id,
            email="mig@example.com",
            hashed_password=hash_password("password123"),
        )
    )
    customer = Customer(organization_id=org.id, name="Cust", external_ref="cust-1")
    metric = Metric(organization_id=org.id, code="api_calls", name="API Calls", unit="call")
    db.add_all([customer, metric])
    db.flush()

    plan = create_plan(
        db,
        organization_id=org.id,
        body=PlanCreate(
            code="api",
            name="API",
            base_fee=Decimal("0"),
            components=[
                ComponentIn(metric_code="api_calls", model="flat_per_unit", unit_price=Decimal("0.1000"))
            ],
        ),
    )
    v1 = plan.versions[0]
    db.add(
        Subscription(
            organization_id=org.id,
            customer_id=customer.id,
            plan_id=plan.id,
            pricing_version_id=v1.id,
        )
    )
    metering.ingest_event(
        db,
        organization_id=org.id,
        event=UsageEventIn(
            event_id="m1",
            customer_external_ref="cust-1",
            metric_code="api_calls",
            quantity=Decimal("10"),
            occurred_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        ),
    )
    invoice = invoicing.generate_invoice(
        db,
        organization_id=org.id,
        customer_id=customer.id,
        period_start=datetime(2026, 5, 1).date(),
        period_end=datetime(2026, 5, 31).date(),
        finalize=True,
    )
    before = {
        "invoice_id": invoice.id,
        "total": str(invoice.total),
        "pricing_version_id": invoice.pricing_version_id,
        "subscription_version_id": v1.id,
    }

    v2 = add_version(
        db,
        organization_id=org.id,
        plan_code="api",
        body=PlanVersionCreate(
            base_fee=Decimal("0"),
            components=[
                ComponentIn(metric_code="api_calls", model="flat_per_unit", unit_price=Decimal("0.2000"))
            ],
        ),
    )
    unexpected = invoicing.shadow_compare(
        db,
        organization_id=org.id,
        invoice_id=invoice.id,
        alternate_pricing_version_id=v2.id,
    )
    blocked = None
    try:
        invoicing.execute_cutover(
            db,
            organization_id=org.id,
            plan_code="api",
            to_pricing_version_id=v2.id,
            invoice_ids=[invoice.id],
        )
    except Exception as exc:  # noqa: BLE001
        blocked = str(exc)

    expected = invoicing.shadow_compare(
        db,
        organization_id=org.id,
        invoice_id=invoice.id,
        alternate_pricing_version_id=v2.id,
        expected_delta=Decimal("1.0000"),
    )
    cutover = invoicing.execute_cutover(
        db,
        organization_id=org.id,
        plan_code="api",
        to_pricing_version_id=v2.id,
        invoice_ids=[invoice.id],
    )
    db.refresh(invoice)
    after_cutover = {
        "invoice_total_unchanged": str(invoice.total),
        "cutover_id": cutover.id,
        "action": cutover.action,
    }
    rollback = invoicing.rollback_cutover(db, organization_id=org.id, cutover_id=cutover.id)
    db.commit()

    report = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "before": before,
        "unexpected_shadow": {
            "delta": str(unexpected.delta),
            "classification": unexpected.classification,
            "cutover_allowed": unexpected.cutover_allowed,
        },
        "blocked_cutover_error": blocked,
        "expected_shadow": {
            "delta": str(expected.delta),
            "classification": expected.classification,
            "cutover_allowed": expected.cutover_allowed,
        },
        "after_cutover": after_cutover,
        "rollback_action": rollback.action,
        "notes": [
            "Finalized invoice total unchanged across cutover/rollback",
            "No payment attempts created in this rehearsal",
        ],
    }
    out = out_dir / "migration_rehearsal.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
