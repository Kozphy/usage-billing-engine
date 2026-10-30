import json

from sqlalchemy.orm import sessionmaker

from app.models import OutboxMessage, OutboxStatus, Organization
from app.services import outbox


def test_bounded_retries_then_terminal_failure(db_engine):
    Session = sessionmaker(bind=db_engine, future=True)
    db = Session()
    org = Organization(name="Retry Org")
    db.add(org)
    db.flush()
    msg = OutboxMessage(
        organization_id=org.id,
        topic="usage.force_fail",
        payload_json=json.dumps({"error": "boom"}),
        status=OutboxStatus.pending,
        max_attempts=3,
    )
    db.add(msg)
    db.commit()

    for _ in range(5):
        outbox.process_pending(db, limit=10, worker_id="t1")
        db.commit()
        db.refresh(msg)
        if msg.status == OutboxStatus.failed:
            break

    assert msg.status == OutboxStatus.failed
    assert msg.attempts == 3
    assert msg.last_error is not None


def test_crash_recovery_reclaims_processing(db_engine):
    Session = sessionmaker(bind=db_engine, future=True)
    db = Session()
    org = Organization(name="Crash Org")
    db.add(org)
    db.flush()
    msg = OutboxMessage(
        organization_id=org.id,
        topic="usage.force_fail",
        payload_json=json.dumps({"error": "temp"}),
        status=OutboxStatus.processing,
        locked_by="dead-worker",
        attempts=1,
        max_attempts=5,
    )
    db.add(msg)
    db.commit()

    n = outbox.recover_stale_processing(db, older_than_seconds=0)
    db.commit()
    db.refresh(msg)
    assert n >= 1
    assert msg.status == OutboxStatus.pending
    assert msg.locked_by is None
