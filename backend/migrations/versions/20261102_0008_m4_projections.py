"""M4 fixture, lifecycle, and portfolio projections.

Revision ID: 20261102_0008
Revises: 20261101_0007
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261102_0008"
down_revision: str | None = "20261101_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("markets", sa.Column("fixture_key", sa.String(66), nullable=True))
    op.add_column("markets", sa.Column("final_outcome", sa.Integer(), nullable=True))
    op.create_index("ix_markets_fixture_key", "markets", ["fixture_key"])
    op.create_table(
        "indexed_fixture_registrations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_address", sa.String(42), nullable=False),
        sa.Column("fixture_key", sa.String(66), nullable=False),
        sa.Column("registrar", sa.String(42), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("revision_hash", sa.String(66), nullable=False),
        sa.Column("market_id", sa.BigInteger(), nullable=True),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column("block_hash", sa.String(66), nullable=False),
        sa.Column("transaction_hash", sa.String(66), nullable=False),
        sa.Column("log_index", sa.Integer(), nullable=False),
        sa.UniqueConstraint("chain_id", "contract_address", "fixture_key", name="uq_indexed_fixture_key"),
    )
    op.create_index("ix_indexed_fixture_registrations_fixture_key", "indexed_fixture_registrations", ["fixture_key"])
    op.create_table(
        "indexed_market_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_address", sa.String(42), nullable=False),
        sa.Column("market_id", sa.BigInteger(), nullable=True),
        sa.Column("event_name", sa.String(80), nullable=False),
        sa.Column("actor", sa.String(42), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column("block_hash", sa.String(66), nullable=False),
        sa.Column("transaction_hash", sa.String(66), nullable=False),
        sa.Column("log_index", sa.Integer(), nullable=False),
        sa.UniqueConstraint("chain_id", "transaction_hash", "log_index", name="uq_indexed_market_event_log"),
    )
    op.create_index("ix_indexed_market_events_event_name", "indexed_market_events", ["event_name"])
    op.create_index("ix_indexed_market_events_actor", "indexed_market_events", ["actor"])
    op.create_index("ix_indexed_market_events_market_order", "indexed_market_events", ["chain_id", "contract_address", "market_id", "block_number", "log_index"])
    op.create_table(
        "indexed_positions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_address", sa.String(42), nullable=False),
        sa.Column("market_id", sa.BigInteger(), nullable=False),
        sa.Column("wallet_address", sa.String(42), nullable=False),
        sa.Column("yes_shares", sa.Numeric(78, 0), nullable=False),
        sa.Column("no_shares", sa.Numeric(78, 0), nullable=False),
        sa.Column("claimed", sa.Boolean(), nullable=False),
        sa.Column("payout", sa.Numeric(78, 0), nullable=False),
        sa.Column("updated_block_number", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("chain_id", "contract_address", "market_id", "wallet_address", name="uq_indexed_position"),
    )
    op.create_index("ix_indexed_positions_wallet", "indexed_positions", ["chain_id", "contract_address", "wallet_address"])


def downgrade() -> None:
    op.drop_index("ix_indexed_positions_wallet", table_name="indexed_positions")
    op.drop_table("indexed_positions")
    op.drop_index("ix_indexed_market_events_market_order", table_name="indexed_market_events")
    op.drop_index("ix_indexed_market_events_actor", table_name="indexed_market_events")
    op.drop_index("ix_indexed_market_events_event_name", table_name="indexed_market_events")
    op.drop_table("indexed_market_events")
    op.drop_index("ix_indexed_fixture_registrations_fixture_key", table_name="indexed_fixture_registrations")
    op.drop_table("indexed_fixture_registrations")
    op.drop_index("ix_markets_fixture_key", table_name="markets")
    op.drop_column("markets", "final_outcome")
    op.drop_column("markets", "fixture_key")
