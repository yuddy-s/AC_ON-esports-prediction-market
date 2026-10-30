"""Add append-only oracle result assessments.

Revision ID: 20261029_0004
Revises: 20261029_0003
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261029_0004"
down_revision: str | None = "20261029_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oracle_result_assessments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.id"), nullable=False),
        sa.Column("observation_id", sa.Integer(), sa.ForeignKey("fixture_result_observations.id"), nullable=False),
        sa.Column("outcome", sa.String(8), nullable=False),
        sa.Column("conflicts_with_prior", sa.Boolean(), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("observation_id", name="uq_oracle_assessment_observation"),
    )
    op.create_index("ix_oracle_result_assessments_fixture_id", "oracle_result_assessments", ["fixture_id"])


def downgrade() -> None:
    op.drop_index("ix_oracle_result_assessments_fixture_id", table_name="oracle_result_assessments")
    op.drop_table("oracle_result_assessments")
