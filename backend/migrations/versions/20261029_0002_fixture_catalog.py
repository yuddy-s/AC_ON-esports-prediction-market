"""Add the M4 off-chain fixture catalog and append-only result observations.

Revision ID: 20261029_0002
Revises: 20261018_0001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261029_0002"
down_revision: str | None = "20261018_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fixtures",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider_id", sa.String(80), nullable=False),
        sa.Column("game_id", sa.String(80), nullable=False),
        sa.Column("external_match_id", sa.String(160), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("match_status", sa.String(32), nullable=False),
        sa.Column("team_a_id", sa.String(160), nullable=False),
        sa.Column("team_a_name", sa.String(160), nullable=False),
        sa.Column("team_b_id", sa.String(160), nullable=False),
        sa.Column("team_b_name", sa.String(160), nullable=False),
        sa.Column("evidence_url", sa.Text(), nullable=True),
        sa.Column("evidence_hash", sa.String(66), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider_id", "game_id", "external_match_id", name="uq_fixture_source_identity"),
    )
    op.create_index("ix_fixtures_scheduled_start", "fixtures", ["scheduled_start"])
    op.create_index("ix_fixtures_game_status", "fixtures", ["game_id", "match_status"])
    op.create_table(
        "fixture_result_observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_status", sa.String(32), nullable=False),
        sa.Column("winner_team_id", sa.String(160), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_url", sa.Text(), nullable=False),
        sa.Column("evidence_hash", sa.String(66), nullable=False),
        sa.Column("observation_hash", sa.String(64), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("fixture_id", "observation_hash", name="uq_fixture_result_observation_hash"),
    )
    op.create_index("ix_fixture_result_observations_fixture_id", "fixture_result_observations", ["fixture_id"])


def downgrade() -> None:
    op.drop_index("ix_fixture_result_observations_fixture_id", table_name="fixture_result_observations")
    op.drop_table("fixture_result_observations")
    op.drop_index("ix_fixtures_game_status", table_name="fixtures")
    op.drop_index("ix_fixtures_scheduled_start", table_name="fixtures")
    op.drop_table("fixtures")
