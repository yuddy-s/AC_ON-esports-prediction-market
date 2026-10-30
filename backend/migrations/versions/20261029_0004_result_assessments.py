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
    op.create_table(
        "oracle_proposal_intents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_address", sa.String(42), nullable=False),
        sa.Column("market_id", sa.BigInteger(), nullable=False),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.id"), nullable=False),
        sa.Column("observation_id", sa.Integer(), sa.ForeignKey("fixture_result_observations.id"), nullable=False),
        sa.Column("outcome", sa.String(8), nullable=False),
        sa.Column("evidence_url", sa.Text(), nullable=False),
        sa.Column("evidence_hash", sa.String(66), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("transaction_hash", sa.String(66), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correction_observation_id", sa.Integer(), sa.ForeignKey("fixture_result_observations.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("chain_id", "contract_address", "market_id", name="uq_oracle_intent_market"),
    )
    op.create_table(
        "oracle_proposal_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("intent_id", sa.Integer(), sa.ForeignKey("oracle_proposal_intents.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("transaction_hash", sa.String(66), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_oracle_proposal_events_intent_id", "oracle_proposal_events", ["intent_id"])


def downgrade() -> None:
    op.drop_index("ix_oracle_proposal_events_intent_id", table_name="oracle_proposal_events")
    op.drop_table("oracle_proposal_events")
    op.drop_table("oracle_proposal_intents")
    op.drop_index("ix_oracle_result_assessments_fixture_id", table_name="oracle_result_assessments")
    op.drop_table("oracle_result_assessments")
