from collections.abc import Sequence
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.indexer.provider import ChainLog
from app.indexer.service import EventIndexer, IndexerConfig
from app.models import IndexedMarket, IndexedTrade, IndexerCheckpoint, ProcessedLog


CHAIN_ID = 11155111
CONTRACT = "0x1111111111111111111111111111111111111111"


def _hash(value: int) -> str:
    return f"0x{value:064x}"


def market_created(block: int, market_id: int = 0, *, suffix: int = 1) -> ChainLog:
    return ChainLog(
        chain_id=CHAIN_ID,
        contract_address=CONTRACT,
        block_number=block,
        block_hash=_hash(block),
        transaction_hash=_hash(block * 100 + suffix),
        log_index=0,
        event_name="MarketCreated",
        payload={
            "market_id": market_id,
            "creator": "0x2222222222222222222222222222222222222222",
            "question": f"Market {market_id}?",
            "trading_deadline": 1_900_000_000 + market_id,
            "state": "CREATED",
        },
    )


def trade_executed(block: int, *, suffix: int = 2, yes_quantity: int = 10**18) -> ChainLog:
    return ChainLog(
        chain_id=CHAIN_ID,
        contract_address=CONTRACT,
        block_number=block,
        block_hash=_hash(block),
        transaction_hash=_hash(block * 100 + suffix),
        log_index=0,
        event_name="TradeExecuted",
        payload={
            "market_id": 0,
            "trader": "0x3333333333333333333333333333333333333333",
            "outcome": 1,
            "shares": str(10**18),
            "cost": str(5 * 10**17),
            "yes_quantity": str(yes_quantity),
            "no_quantity": "0",
        },
    )


class FakeProvider:
    def __init__(self, latest: int, logs: Sequence[ChainLog] = ()) -> None:
        self.latest = latest
        self.logs = list(logs)
        self.hashes = {block: _hash(block) for block in range(latest + 1)}
        self.requested_ranges: list[tuple[int, int]] = []
        self.fail_range: tuple[int, int] | None = None

    def latest_block(self) -> int:
        return self.latest

    def block_hash(self, block_number: int) -> str:
        return self.hashes[block_number]

    def get_logs(self, contract_address: str, from_block: int, to_block: int) -> Sequence[ChainLog]:
        self.requested_ranges.append((from_block, to_block))
        if self.fail_range == (from_block, to_block):
            raise RuntimeError("simulated RPC failure")
        return [log for log in self.logs if from_block <= log.block_number <= to_block]


@pytest.fixture()
def session(tmp_path: Path) -> Session:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'indexer.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as database_session:
        yield database_session


def indexer(provider: FakeProvider, *, batch_size: int = 500) -> EventIndexer:
    return EventIndexer(
        provider,
        IndexerConfig(
            chain_id=CHAIN_ID,
            contract_address=CONTRACT,
            deployment_block=1,
            confirmation_depth=0,
            block_batch_size=batch_size,
        ),
    )


def test_duplicate_log_delivery_is_applied_once(session: Session) -> None:
    event = market_created(1)
    provider = FakeProvider(1, [event, event])

    result = indexer(provider).sync_once(session)

    assert result.processed_logs == 1
    assert session.scalar(select(func.count()).select_from(ProcessedLog)) == 1
    assert session.scalar(select(func.count()).select_from(IndexedMarket)) == 1


def test_restart_resumes_after_last_checkpoint(session: Session) -> None:
    provider = FakeProvider(2, [market_created(1)])
    first_indexer = indexer(provider)
    first_indexer.sync_once(session)

    provider.latest = 4
    provider.hashes.update({3: _hash(3), 4: _hash(4)})
    provider.logs.append(trade_executed(4))
    provider.requested_ranges.clear()
    indexer(provider).sync_once(session)

    assert provider.requested_ranges == [(3, 4)]
    checkpoint = session.scalar(select(IndexerCheckpoint))
    assert checkpoint is not None
    assert checkpoint.next_block == 5
    assert session.scalar(select(func.count()).select_from(IndexedTrade)) == 1


def test_missed_ranges_are_scanned_in_bounded_batches(session: Session) -> None:
    provider = FakeProvider(5, [market_created(1), trade_executed(5)])

    result = indexer(provider, batch_size=2).sync_once(session)

    assert result.batches == 3
    assert provider.requested_ranges == [(1, 2), (3, 4), (5, 5)]
    assert session.scalar(select(func.count()).select_from(IndexedTrade)) == 1


def test_confirmation_depth_leaves_recent_blocks_unindexed(session: Session) -> None:
    provider = FakeProvider(5, [market_created(1), trade_executed(4)])
    service = EventIndexer(
        provider,
        IndexerConfig(
            chain_id=CHAIN_ID,
            contract_address=CONTRACT,
            deployment_block=1,
            confirmation_depth=2,
            block_batch_size=10,
        ),
    )

    result = service.sync_once(session)

    assert result.latest_observed_block == 5
    assert result.last_safe_block == 3
    assert session.scalar(select(func.count()).select_from(IndexedTrade)) == 0


def test_rpc_failure_does_not_advance_failed_range(session: Session) -> None:
    provider = FakeProvider(4, [market_created(1)])
    provider.fail_range = (3, 4)

    with pytest.raises(RuntimeError, match="simulated RPC failure"):
        indexer(provider, batch_size=2).sync_once(session)

    checkpoint = session.scalar(select(IndexerCheckpoint))
    assert checkpoint is not None
    assert checkpoint.last_safe_block == 2
    assert checkpoint.next_block == 3


def test_projection_and_checkpoint_are_atomic_per_batch(session: Session) -> None:
    malformed_trade = trade_executed(2)
    malformed_trade.payload.pop("cost")
    provider = FakeProvider(2, [market_created(1), malformed_trade])

    with pytest.raises(KeyError, match="cost"):
        indexer(provider).sync_once(session)

    checkpoint = session.scalar(select(IndexerCheckpoint))
    assert checkpoint is not None
    assert checkpoint.next_block == 1
    assert session.scalar(select(func.count()).select_from(ProcessedLog)) == 0
    assert session.scalar(select(func.count()).select_from(IndexedMarket)) == 0


def test_checkpoint_hash_mismatch_rebuilds_canonical_projection(session: Session) -> None:
    provider = FakeProvider(2, [market_created(1), trade_executed(2, yes_quantity=10**18)])
    indexer(provider).sync_once(session)

    provider.hashes[2] = _hash(999)
    replacement_market = market_created(1)
    replacement_trade = trade_executed(2, suffix=9, yes_quantity=2 * 10**18)
    replacement_trade = ChainLog(
        chain_id=replacement_trade.chain_id,
        contract_address=replacement_trade.contract_address,
        block_number=replacement_trade.block_number,
        block_hash=_hash(999),
        transaction_hash=replacement_trade.transaction_hash,
        log_index=replacement_trade.log_index,
        event_name=replacement_trade.event_name,
        payload=replacement_trade.payload,
    )
    provider.logs = [replacement_market, replacement_trade]

    result = indexer(provider).sync_once(session)

    assert result.rebuilt_after_reorg is True
    market = session.scalar(select(IndexedMarket))
    assert market is not None
    assert market.yes_quantity == 2 * 10**18
    assert session.scalar(select(func.count()).select_from(IndexedTrade)) == 1


def test_explicit_rebuild_is_deterministic(session: Session) -> None:
    provider = FakeProvider(2, [market_created(1), trade_executed(2)])
    service = indexer(provider)
    service.sync_once(session)
    original = session.scalar(select(IndexedMarket))
    assert original is not None
    original_projection = (original.question, original.yes_quantity, original.source_transaction_hash)

    result = service.rebuild(session)

    rebuilt = session.scalar(select(IndexedMarket))
    assert rebuilt is not None
    assert result.processed_logs == 2
    assert (rebuilt.question, rebuilt.yes_quantity, rebuilt.source_transaction_hash) == original_projection
    assert session.scalar(select(func.count()).select_from(ProcessedLog)) == 2
