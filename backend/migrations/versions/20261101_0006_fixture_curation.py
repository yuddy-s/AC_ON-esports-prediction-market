"""Add auditable operator curation for provider-sourced fixtures.

Revision ID: 20261101_0006
Revises: 20261030_0005
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261101_0006"
down_revision: str | None = "20261030_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("fixtures", sa.Column("curated_evidence_url", sa.Text(), nullable=True))
    op.add_column("fixtures", sa.Column("curated_evidence_hash", sa.String(66), nullable=True))
    op.add_column("fixtures", sa.Column("curated_identity_hash", sa.String(64), nullable=True))
    op.create_table(
        "fixture_review_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.id"), nullable=False),
        sa.Column("reviewer", sa.String(120), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("identity_hash", sa.String(64), nullable=False),
        sa.Column("evidence_url", sa.Text(), nullable=True),
        sa.Column("evidence_hash", sa.String(66), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_fixture_review_events_fixture_id", "fixture_review_events", ["fixture_id"])


def downgrade() -> None:
    op.drop_index("ix_fixture_review_events_fixture_id", table_name="fixture_review_events")
    op.drop_table("fixture_review_events")
    op.drop_column("fixtures", "curated_identity_hash")
    op.drop_column("fixtures", "curated_evidence_hash")
    op.drop_column("fixtures", "curated_evidence_url")
