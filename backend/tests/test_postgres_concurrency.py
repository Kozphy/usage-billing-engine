"""Real PostgreSQL constraint and concurrency proofs.

These tests are skipped when Postgres is unreachable. CI runs them against a
service container. SQLite unit tests are not treated as proof of PG behavior.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models import Customer, Metric, Organization, UsageEvent
from app.services.metering import content_hash

pytestmark = pytest.mark.postgres


def test_unique_event_id_enforced_by_postgres(pg_engine):
    Session = sessionmaker(bind=pg_engine, future=True)
    db = Session()
    org = Organization(name="PG Org")
    db.add(org)
    db.flush()
    customer = Customer(organization_id=org.id, name="C", external_ref="c1")
    metric = Metric(organization_id=org.id, code="units", name="Units", unit="unit")
    db.add_all([customer, metric])
    db.flush()
    digest = content_hash(
        customer_id=customer.id,
        metric_id=metric.id,
        quantity=Decimal("1"),
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        schema_version=1,
    )
    db.add(
        UsageEvent(
            organization_id=org.id,
            customer_id=customer.id,
            metric_id=metric.id,
            event_id="dup",
            quantity=Decimal("1"),
            occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            content_hash=digest,
            status="applied",
        )
    )
    db.commit()

    db2 = Session()
    with pytest.raises(IntegrityError):
        db2.add(
            UsageEvent(
                organization_id=org.id,
                customer_id=customer.id,
                metric_id=metric.id,
                event_id="dup",
                quantity=Decimal("1"),
                occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                content_hash=digest,
                status="applied",
            )
        )
        db2.commit()
    db2.rollback()
    db.close()
    db2.close()


def test_concurrent_duplicate_submissions_one_winner(pg_engine):
    Session = sessionmaker(bind=pg_engine, future=True)
    setup = Session()
    org = Organization(name="Conc Org")
    setup.add(org)
    setup.flush()
    customer = Customer(organization_id=org.id, name="C", external_ref="c1")
    metric = Metric(organization_id=org.id, code="units", name="Units", unit="unit")
    setup.add_all([customer, metric])
    setup.commit()
    org_id, customer_id, metric_id = org.id, customer.id, metric.id
    setup.close()

    barrier = threading.Barrier(2)
    results: list[str] = []

    def attempt(label: str) -> None:
        db = Session()
        barrier.wait()
        digest = content_hash(
            customer_id=customer_id,
            metric_id=metric_id,
            quantity=Decimal("3"),
            occurred_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            schema_version=1,
        )
        try:
            db.add(
                UsageEvent(
                    organization_id=org_id,
                    customer_id=customer_id,
                    metric_id=metric_id,
                    event_id="race-1",
                    quantity=Decimal("3"),
                    occurred_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
                    content_hash=digest,
                    status="pending",
                )
            )
            db.commit()
            results.append(f"{label}:ok")
        except IntegrityError:
            db.rollback()
            results.append(f"{label}:conflict")
        finally:
            db.close()

    t1 = threading.Thread(target=attempt, args=("a",))
    t2 = threading.Thread(target=attempt, args=("b",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert sorted(results).count("a:ok") + sorted(results).count("b:ok") == 1
    assert any(r.endswith(":conflict") for r in results)

    from sqlalchemy import func, select

    db = Session()
    count = db.scalar(
        select(func.count()).select_from(UsageEvent).where(
            UsageEvent.event_id == "race-1",
            UsageEvent.organization_id == org_id,
        )
    )
    assert count == 1
    db.close()
