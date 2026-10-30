import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force test settings before app import
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["OUTBOX_SYNC"] = "true"
os.environ["PAYMENT_PROVIDER"] = "mock"
os.environ["SECRET_KEY"] = "test-secret-key"

from app.db import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_engine):
    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, future=True)

    def _override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    res = client.post(
        "/auth/register",
        json={
            "organization_name": "Demo Org",
            "email": "ops@example.com",
            "password": "password123",
        },
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    org_id = res.json()["organization_id"]
    return {"Authorization": f"Bearer {token}"}, org_id
