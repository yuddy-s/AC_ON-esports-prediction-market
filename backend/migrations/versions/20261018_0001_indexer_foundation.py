"""Add deterministic indexer projection tables.

Revision ID: 20261018_0001
Revises:
Create Date: 2026-10-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261018_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Milestone 2 created this table with SQLAlchemy create_all rather than Alembic.
    # Adopt it when present and create it for fresh installations.
    op.create_table(
        "sample_matches",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("game", sa.String(length=80), nullable=False),
        sa.Column("league", sa.String(length=120), nullable=False),
        sa.Column("team_a", sa.String(length=120), nullable=False),
        sa.Column("team_b", sa.String(length=120), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("market_label", sa.String(length=160), nullable=False),
        sa.Column("yes_price", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("no_price", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("source_note", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("slug"),
        if_not_exists=True,
    )
    op.create_table(
        "indexed_contracts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_address", sa.String(length=42), nullable=False),
        sa.Column("deployment_block", sa.BigInteger(), nullable=False),
        sa.Column("abi_version", sa.String(length=80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chain_id", "contract_address", name="uq_indexed_contract_chain_address"),
    )
    op.create_table(
        "indexer_checkpoints",
        sa.Column("indexed_contract_id", sa.Integer(), nullable=False),
        sa.Column("next_block", sa.BigInteger(), nullable=False),
        sa.Column("last_safe_block", sa.BigInteger(), nullable=True),
        sa.Column("last_safe_block_hash", sa.String(length=66), nullable=True),
        sa.Column("latest_observed_block", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["indexed_contract_id"], ["indexed_contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("indexed_contract_id"),
    )
    op.create_table(
        "processed_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("indexed_contract_id", sa.Integer(), nullable=False),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_address", sa.String(length=42), nullable=False),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column("block_hash", sa.String(length=66), nullable=False),
        sa.Column("transaction_hash", sa.String(length=66), nullable=False),
        sa.Column("log_index", sa.Integer(), nullable=False),
        sa.Column("event_name", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["indexed_contract_id"], ["indexed_contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chain_id", "transaction_hash", "log_index", name="uq_processed_log_identity"),
    )
    op.create_index("ix_processed_logs_indexed_contract_id", "processed_logs", ["indexed_contract_id"])
    op.create_index("ix_processed_logs_block_number", "processed_logs", ["block_number"])
    op.create_table(
        "markets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_address", sa.String(length=42), nullable=False),
        sa.Column("market_id", sa.BigInteger(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("trading_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("creator", sa.String(length=42), nullable=False),
        sa.Column("yes_quantity", sa.Numeric(precision=78, scale=0), nullable=False),
        sa.Column("no_quantity", sa.Numeric(precision=78, scale=0), nullable=False),
        sa.Column("source_block_number", sa.BigInteger(), nullable=False),
        sa.Column("source_block_hash", sa.String(length=66), nullable=False),
        sa.Column("source_transaction_hash", sa.String(length=66), nullable=False),
        sa.Column("source_log_index", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chain_id", "contract_address", "market_id", name="uq_market_contract_id"),
    )
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_address", sa.String(length=42), nullable=False),
        sa.Column("market_id", sa.BigInteger(), nullable=False),
        sa.Column("trader", sa.String(length=42), nullable=False),
        sa.Column("outcome", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Numeric(precision=78, scale=0), nullable=False),
        sa.Column("cost", sa.Numeric(precision=78, scale=0), nullable=False),
        sa.Column("yes_quantity", sa.Numeric(precision=78, scale=0), nullable=False),
        sa.Column("no_quantity", sa.Numeric(precision=78, scale=0), nullable=False),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column("block_hash", sa.String(length=66), nullable=False),
        sa.Column("transaction_hash", sa.String(length=66), nullable=False),
        sa.Column("log_index", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chain_id", "transaction_hash", "log_index", name="uq_trade_log_identity"),
    )
    op.create_index("ix_trades_market_id", "trades", ["market_id"])


def downgrade() -> None:
    op.drop_index("ix_trades_market_id", table_name="trades")
    op.drop_table("trades")
    op.drop_table("markets")
    op.drop_index("ix_processed_logs_block_number", table_name="processed_logs")
    op.drop_index("ix_processed_logs_indexed_contract_id", table_name="processed_logs")
    op.drop_table("processed_logs")
    op.drop_table("indexer_checkpoints")
    op.drop_table("indexed_contracts")
    # Preserve sample_matches because it can predate Alembic adoption.
