"""SQLAlchemy engine, session factory, and FastAPI dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def _make_engine():
    """Create the process-wide SQLAlchemy engine from settings.

    Returns:
        Configured ``Engine`` (SQLite enables foreign keys via PRAGMA).
    """
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
    if settings.database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped database session.

    Yields:
        SQLAlchemy ``Session`` closed when the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
