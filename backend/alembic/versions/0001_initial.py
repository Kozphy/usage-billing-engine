"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-29
"""

from typing import Sequence, Union

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema is created via SQLAlchemy metadata in local/dev; this revision
    # documents the baseline for Postgres deployments. Prefer `alembic revision --autogenerate`
    # against a live DATABASE_URL for production DDL.
    pass


def downgrade() -> None:
    pass
