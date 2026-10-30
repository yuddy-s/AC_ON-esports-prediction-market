"""Retain each signed fixture snapshot in registrar audit history.

Revision ID: 20261030_0005
Revises: 20261029_0004
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261030_0005"
down_revision: str | None = "20261029_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("registration_job_events", sa.Column("fixture_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("registration_job_events", "fixture_snapshot")
