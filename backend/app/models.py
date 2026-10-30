from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SampleMatch(Base):
    __tablename__ = "sample_matches"

    slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    game: Mapped[str] = mapped_column(String(80), nullable=False)
    league: Mapped[str] = mapped_column(String(120), nullable=False)
    team_a: Mapped[str] = mapped_column(String(120), nullable=False)
    team_b: Mapped[str] = mapped_column(String(120), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    market_label: Mapped[str] = mapped_column(String(160), nullable=False)
    yes_price: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    no_price: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    source_note: Mapped[str] = mapped_column(Text, nullable=False)


class Fixture(Base):
    """Imported source data; never an authoritative on-chain registration."""

    __tablename__ = "fixtures"
    __table_args__ = (
        UniqueConstraint("provider_id", "game_id", "external_match_id", name="uq_fixture_source_identity"),
        Index("ix_fixtures_scheduled_start", "scheduled_start"),
        Index("ix_fixtures_game_status", "game_id", "match_status"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(String(80), nullable=False)
    game_id: Mapped[str] = mapped_column(String(80), nullable=False)
    external_match_id: Mapped[str] = mapped_column(String(160), nullable=False)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    match_status: Mapped[str] = mapped_column(String(32), nullable=False)
    team_a_id: Mapped[str] = mapped_column(String(160), nullable=False)
    team_a_name: Mapped[str] = mapped_column(String(160), nullable=False)
    team_b_id: Mapped[str] = mapped_column(String(160), nullable=False)
    team_b_name: Mapped[str] = mapped_column(String(160), nullable=False)
    evidence_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class FixtureResultObservation(Base):
    """Append-only result source history; corrections do not rewrite earlier observations."""

    __tablename__ = "fixture_result_observations"
    __table_args__ = (
        UniqueConstraint("fixture_id", "observation_hash", name="uq_fixture_result_observation_hash"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id", ondelete="CASCADE"), nullable=False, index=True)
    match_status: Mapped[str] = mapped_column(String(32), nullable=False)
    winner_team_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_url: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    observation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class IndexedContract(Base):
    __tablename__ = "indexed_contracts"
    __table_args__ = (
        UniqueConstraint("chain_id", "contract_address", name="uq_indexed_contract_chain_address"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False)
    deployment_block: Mapped[int] = mapped_column(BigInteger, nullable=False)
    abi_version: Mapped[str] = mapped_column(String(80), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class IndexerCheckpoint(Base):
    __tablename__ = "indexer_checkpoints"

    indexed_contract_id: Mapped[int] = mapped_column(
        ForeignKey("indexed_contracts.id", ondelete="CASCADE"), primary_key=True
    )
    next_block: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_safe_block: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_safe_block_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    latest_observed_block: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class ProcessedLog(Base):
    __tablename__ = "processed_logs"
    __table_args__ = (
        UniqueConstraint("chain_id", "transaction_hash", "log_index", name="uq_processed_log_identity"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indexed_contract_id: Mapped[int] = mapped_column(
        ForeignKey("indexed_contracts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chain_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False)
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    block_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    transaction_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    log_index: Mapped[int] = mapped_column(Integer, nullable=False)
    event_name: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)


class IndexedMarket(Base):
    __tablename__ = "markets"
    __table_args__ = (
        UniqueConstraint("chain_id", "contract_address", "market_id", name="uq_market_contract_id"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False)
    market_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    trading_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    creator: Mapped[str] = mapped_column(String(42), nullable=False)
    yes_quantity: Mapped[Decimal] = mapped_column(Numeric(78, 0), nullable=False, default=0)
    no_quantity: Mapped[Decimal] = mapped_column(Numeric(78, 0), nullable=False, default=0)
    source_block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_block_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    source_transaction_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    source_log_index: Mapped[int] = mapped_column(Integer, nullable=False)


class IndexedTrade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        UniqueConstraint("chain_id", "transaction_hash", "log_index", name="uq_trade_log_identity"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chain_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    contract_address: Mapped[str] = mapped_column(String(42), nullable=False)
    market_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    trader: Mapped[str] = mapped_column(String(42), nullable=False)
    outcome: Mapped[int] = mapped_column(Integer, nullable=False)
    shares: Mapped[Decimal] = mapped_column(Numeric(78, 0), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(78, 0), nullable=False)
    yes_quantity: Mapped[Decimal] = mapped_column(Numeric(78, 0), nullable=False)
    no_quantity: Mapped[Decimal] = mapped_column(Numeric(78, 0), nullable=False)
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    block_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    transaction_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    log_index: Mapped[int] = mapped_column(Integer, nullable=False)
