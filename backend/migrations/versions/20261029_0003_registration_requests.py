"""Store single-use registration challenges and one request per fixture.

Revision ID: 20261029_0003
Revises: 20261029_0002
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261029_0003"
down_revision: str | None = "20261029_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "registration_challenges",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.id"), nullable=False),
        sa.Column("wallet_address", sa.String(42), nullable=False),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("nonce_hash", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("nonce_hash", name="uq_registration_nonce_hash"),
    )
    op.create_index("ix_registration_challenges_fixture_id", "registration_challenges", ["fixture_id"])
    op.create_index("ix_registration_challenges_wallet_address", "registration_challenges", ["wallet_address"])
    op.create_table(
        "fixture_registration_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("fixture_id", sa.Integer(), sa.ForeignKey("fixtures.id"), nullable=False),
        sa.Column("requested_by", sa.String(42), nullable=False),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("transaction_hash", sa.String(66), nullable=True),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("fixture_id", name="uq_fixture_registration_job"),
    )


def downgrade() -> None:
    op.drop_table("fixture_registration_jobs")
    op.drop_index("ix_registration_challenges_wallet_address", table_name="registration_challenges")
    op.drop_index("ix_registration_challenges_fixture_id", table_name="registration_challenges")
    op.drop_table("registration_challenges")
