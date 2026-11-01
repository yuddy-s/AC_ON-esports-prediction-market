"""Auditable independent result evidence for PandaScore observations.

Revision ID: 20261101_0007
Revises: 20261101_0006
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261101_0007"
down_revision: str | None = "20261101_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "result_review_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("observation_id", sa.Integer(), sa.ForeignKey("fixture_result_observations.id"), nullable=False),
        sa.Column("reviewer", sa.String(120), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("evidence_url", sa.Text(), nullable=True),
        sa.Column("evidence_hash", sa.String(66), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_result_review_events_observation_id", "result_review_events", ["observation_id"])


def downgrade() -> None:
    op.drop_index("ix_result_review_events_observation_id", table_name="result_review_events")
    op.drop_table("result_review_events")
