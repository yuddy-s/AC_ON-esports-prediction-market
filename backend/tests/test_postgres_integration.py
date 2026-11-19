"""Production-dialect coverage. CI supplies a disposable migrated PostgreSQL database."""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
import os

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.fixture_data import deterministic_mock
from app.fixture_service import import_document
from app.indexer.provider import ChainLog
from app.indexer.service import EventIndexer, IndexerConfig
from app.m4_api import _market_read
from app.models import (
    Fixture, FixtureRegistrationJob, IndexedMarket, IndexedTrade, OracleProposalEvent,
    OracleProposalIntent, OracleResultAssessment, ProcessedLog, RegistrationJobEvent,
)
from app.oracle_assessment import assess_imported_results
from app.registration_service import fixture_snapshot


pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_POSTGRES_URL", "").startswith("postgresql"),
    reason="requires the disposable PostgreSQL CI service",
)

CHAIN_ID = 911155111
CONTRACT = "0x9999999999999999999999999999999999999999"
MAX_UINT256 = 2**256 - 1


def _hash(value: int) -> str:
    return f"0x{value:064x}"


def _market(block: int = 1) -> ChainLog:
    return ChainLog(
        CHAIN_ID, CONTRACT, block, _hash(block), _hash(100 + block), 0,
        "MarketCreated", {
            "market_id": 0,
            "creator": "0x2222222222222222222222222222222222222222",
            "question": "PostgreSQL preserves uint256 values?",
            "trading_deadline": 1_900_000_000,
            "fixture_key": _hash(42),
        },
    )


def _trade(block: int = 5, *, block_hash: str | None = None, suffix: int = 1) -> ChainLog:
    return ChainLog(
        CHAIN_ID, CONTRACT, block, block_hash or _hash(block), _hash(500 + suffix), 0,
        "TradeExecuted", {
            "market_id": 0,
            "trader": "0x3333333333333333333333333333333333333333",
            "outcome": 0,
            "shares": str(MAX_UINT256),
            "cost": str(MAX_UINT256),
            "yes_quantity": str(MAX_UINT256),
            "no_quantity": "0",
        },
    )


class Provider:
    def __init__(self, logs: Sequence[ChainLog]) -> None:
        self.logs = list(logs)
        self.latest = 5
        self.hashes = {block: _hash(block) for block in range(1, 6)}
        self.requested_ranges: list[tuple[int, int]] = []

    def latest_block(self) -> int:
        return self.latest

    def block_hash(self, block_number: int) -> str:
        return self.hashes[block_number]

    def get_logs(self, _address: str, start: int, end: int) -> Sequence[ChainLog]:
        self.requested_ranges.append((start, end))
        return [log for log in self.logs if start <= log.block_number <= end]


def _service(provider: Provider) -> EventIndexer:
    return EventIndexer(provider, IndexerConfig(
        chain_id=CHAIN_ID,
        contract_address=CONTRACT,
        deployment_block=1,
        confirmation_depth=0,
        block_batch_size=2,
        abi_version="postgres-ci-m4",
        m4_enabled=True,
    ))


def _add_preserved_records(session: Session) -> None:
    import_document(session, deterministic_mock())
    assess_imported_results(session)
    fixture = session.get(Fixture, 1)
    assert fixture is not None
    now = datetime(2030, 1, 2, tzinfo=UTC)
    registration = FixtureRegistrationJob(
        fixture_id=fixture.id,
        requested_by="0x" + "44" * 20,
        chain_id=CHAIN_ID,
        status="awaiting_abi",
        fixture_snapshot=fixture_snapshot(fixture),
        attempts=0,
        created_at=now,
        updated_at=now,
    )
    session.add(registration)
    session.flush()
    session.add(RegistrationJobEvent(
        job_id=registration.id, status="awaiting_abi", recorded_at=now,
    ))
    intent = OracleProposalIntent(
        chain_id=CHAIN_ID,
        contract_address=CONTRACT,
        market_id=0,
        fixture_id=fixture.id,
        observation_id=1,
        outcome="YES",
        evidence_url="https://organizer.example/match/ci",
        evidence_hash="0x" + "11" * 32,
        status="queued",
        attempts=0,
        created_at=now,
        updated_at=now,
    )
    session.add(intent)
    session.flush()
    session.add(OracleProposalEvent(intent_id=intent.id, status="queued", recorded_at=now))
    session.commit()


def test_postgresql_uint256_replay_reorg_and_rebuild_preservation() -> None:
    with SessionLocal() as session:
        _add_preserved_records(session)
        market_log = _market()
        trade_log = _trade()
        provider = Provider([market_log, market_log, trade_log, trade_log])
        service = _service(provider)

        first = service.sync_once(session)
        assert first.processed_logs == 2
        assert provider.requested_ranges == [(1, 2), (3, 4), (5, 5)]
        assert session.scalar(select(func.count()).select_from(ProcessedLog)) == 2
        trade = session.scalar(select(IndexedTrade))
        market = session.scalar(select(IndexedMarket))
        assert trade is not None and market is not None
        assert Decimal(trade.shares) == MAX_UINT256
        assert Decimal(trade.cost) == MAX_UINT256
        assert Decimal(market.yes_quantity) == MAX_UINT256
        assert _market_read(market)["yes_quantity"] == str(MAX_UINT256)

        service.rebuild(session)
        assert session.scalar(select(func.count()).select_from(ProcessedLog)) == 2
        assert Decimal(session.scalar(select(IndexedTrade.shares))) == MAX_UINT256
        for model in (
            Fixture, FixtureRegistrationJob, RegistrationJobEvent, OracleResultAssessment,
            OracleProposalIntent, OracleProposalEvent,
        ):
            assert session.scalar(select(func.count()).select_from(model)) == 1

        provider.hashes[5] = _hash(999)
        provider.logs = [market_log, _trade(block_hash=_hash(999), suffix=2)]
        reorg = service.sync_once(session)
        assert reorg.rebuilt_after_reorg is True
        assert session.scalar(select(func.count()).select_from(ProcessedLog)) == 2
        assert Decimal(session.scalar(select(IndexedTrade.shares))) == MAX_UINT256
