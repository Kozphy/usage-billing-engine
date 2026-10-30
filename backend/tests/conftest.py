import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force test settings before app import
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ["OUTBOX_SYNC"] = "true"
os.environ["PAYMENT_PROVIDER"] = "mock"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["MOCK_PAYMENT_TIMEOUT_RATE"] = "0"
os.environ["OUTBOX_BACKOFF_SECONDS"] = "0"
os.environ["OUTBOX_MAX_ATTEMPTS"] = "5"

from app.config import get_settings  # noqa: E402
from app.db import Base, get_db  # noqa: E402
from app.main import create_app  # noqa: E402

get_settings.cache_clear()


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


def pytest_configure(config):
    config.addinivalue_line("markers", "postgres: requires real PostgreSQL")


@pytest.fixture(scope="session")
def pg_url():
    return os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://billing:billing@127.0.0.1:5433/billing",
    )


@pytest.fixture()
def pg_engine(pg_url):
    """Real Postgres engine for constraint/concurrency tests. Skips if unreachable."""
    try:
        engine = create_engine(
            pg_url,
            future=True,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3},
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres not available at {pg_url}: {exc}")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
