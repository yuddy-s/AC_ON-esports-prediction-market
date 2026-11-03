import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.indexer.decoder import JsonAbiEventDecoder
from app.indexer.provider import ChainLog
from app.indexer.rpc import RawEthereumLog
from app.indexer.service import EventIndexer, IndexerConfig
from app.models import IndexedFixtureRegistration, IndexedMarket, IndexedMarketEvent, IndexedPosition


ROOT = Path(__file__).resolve().parents[2]
CHAIN = 31337
CONTRACT = "0xdc64a140aa3e981100a9beca4e685f962f0cf6c9"
WALLET = "0x15d34aaf54267db7d7c367839aaf71a00a2c6a65"


def _hash(value: int) -> str:
    return f"0x{value:064x}"


def _log(block: int, name: str, payload: dict[str, object]) -> ChainLog:
    return ChainLog(CHAIN, CONTRACT, block, _hash(block), _hash(block * 100), 0, name, payload)


class Provider:
    def __init__(self, logs: list[ChainLog]) -> None:
        self.logs = logs

    def latest_block(self) -> int:
        return max(log.block_number for log in self.logs)

    def block_hash(self, block_number: int) -> str:
        return _hash(block_number)

    def get_logs(self, _address: str, start: int, end: int) -> list[ChainLog]:
        return [log for log in self.logs if start <= log.block_number <= end]


def test_exact_anvil_event_fixtures_decode_with_merged_abi() -> None:
    document = json.loads((ROOT / "deployments/event-fixtures.anvil.json").read_text(encoding="utf-8"))
    decoder = JsonAbiEventDecoder(ROOT / "deployments/abi/PredictionMarket.abi.json")
    decoded_names = set()
    for fixture in document["fixtures"]:
        raw = fixture["raw_log"]
        decoded = decoder.decode(CHAIN, RawEthereumLog(
            address=raw["address"].lower(),
            block_number=int(raw["blockNumber"], 16),
            block_hash=raw["blockHash"].lower(),
            transaction_hash=raw["transactionHash"].lower(),
            log_index=int(raw["logIndex"], 16),
            topics=tuple(topic.lower() for topic in raw["topics"]),
            data=raw["data"].lower(),
        ))
        assert decoded is not None
        assert decoded.event_name == fixture["event_name"]
        decoded_names.add(decoded.event_name)
    assert {
        "FixtureRegistered", "MarketCreated", "TradeExecuted", "SellExecuted",
        "OutcomeProposed", "OutcomeChallenged", "ResolverCommitteeSelected",
        "ResolverVoteCast", "MarketFinalized", "MarketVoided", "PayoutClaimed",
    } <= decoded_names


def test_m4_projection_tracks_fixture_market_position_resolution_and_claim(tmp_path: Path) -> None:
    key = "0x" + "11" * 32
    logs = [
        _log(1, "FixtureRegistered", {"fixture_key": key, "registrar": WALLET, "data": {"provider_id": "pandascore"}, "revision_hash": _hash(9)}),
        _log(2, "MarketCreated", {"market_id": 7, "creator": WALLET, "question": "A beats B?", "trading_deadline": 1_900_000_000, "fixture_key": key}),
        _log(3, "TradeExecuted", {"market_id": 7, "trader": WALLET, "outcome": 0, "shares": 10**18, "cost": 5 * 10**17, "yes_quantity": 10**18, "no_quantity": 0}),
        _log(4, "SellExecuted", {"market_id": 7, "trader": WALLET, "outcome": 0, "shares": 2 * 10**17, "proceeds": 10**17, "yes_quantity": 8 * 10**17, "no_quantity": 0}),
        _log(5, "OutcomeProposed", {"market_id": 7, "proposer": WALLET, "outcome": 0, "evidence_hash": _hash(8), "evidence_uri": "https://example.org", "challenge_deadline": 2_000_000_000}),
        _log(6, "MarketFinalized", {"market_id": 7, "outcome": 0, "remaining_liability": 8 * 10**17}),
        _log(7, "PayoutClaimed", {"market_id": 7, "account": WALLET, "payout": 8 * 10**17, "yes_shares": 8 * 10**17, "no_shares": 0, "remaining_liability": 0}),
    ]
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'm4.db'}")
    Base.metadata.create_all(engine)
    Local = sessionmaker(bind=engine, autoflush=False)
    with Local() as session:
        service = EventIndexer(Provider(logs), IndexerConfig(
            chain_id=CHAIN, contract_address=CONTRACT, deployment_block=1,
            confirmation_depth=0, m4_enabled=True, abi_version="m4",
        ))
        service.sync_once(session)
        registration = session.scalar(select(IndexedFixtureRegistration))
        market = session.scalar(select(IndexedMarket))
        position = session.scalar(select(IndexedPosition))
        events = session.scalars(select(IndexedMarketEvent).order_by(IndexedMarketEvent.block_number)).all()
        assert registration is not None and registration.market_id == 7
        assert market is not None and market.state == "FINALIZED" and market.final_outcome == 0
        assert position is not None and position.claimed and position.yes_shares == 0
        assert position.payout == 8 * 10**17
        assert [event.event_name for event in events] == [
            "MarketCreated", "TradeExecuted", "SellExecuted", "OutcomeProposed",
            "MarketFinalized", "PayoutClaimed",
        ]
        first_snapshot = (
            registration.market_id, market.state, market.final_outcome,
            position.yes_shares, position.payout,
            [(event.event_name, event.payload) for event in events],
        )
        service.rebuild(session)
        registration = session.scalar(select(IndexedFixtureRegistration))
        market = session.scalar(select(IndexedMarket))
        position = session.scalar(select(IndexedPosition))
        events = session.scalars(select(IndexedMarketEvent).order_by(IndexedMarketEvent.block_number)).all()
        assert registration is not None and market is not None and position is not None
        assert (
            registration.market_id, market.state, market.final_outcome,
            position.yes_shares, position.payout,
            [(event.event_name, event.payload) for event in events],
        ) == first_snapshot
