"""Issue #53: the shared deadline vectors, checked against the indexed API.

Each vector in docs/agent/testing/vectors/market_deadline_vectors.json is
projected from its matching lifecycle events, then read back through
GET /api/v2/markets/{id}. The API must return the raw stored state and the
stored trading deadline:

- An OPEN market whose deadline has passed stays OPEN. Time passing emits no
  event, so the backend must not derive or mutate state (no second lifecycle
  authority).
- After a registrar early close the stored deadline is the shortened value
  carried by the MarketClosed event, not the creation-time deadline.

The contract-side expectations (tradeAccepted and friends) and the frontend
actions belong to the other layers' tests and are deliberately not asserted
here.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import Generator

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_deadline_vectors.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_session
from app.indexer.provider import ChainLog
from app.indexer.service import EventIndexer, IndexerConfig
from app.main import app


ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "docs/agent/testing/vectors/market_deadline_vectors.json"
CHAIN = 31337
CONTRACT = "0xdc64a140aa3e981100a9beca4e685f962f0cf6c9"
WALLET = "0x15d34aaf54267db7d7c367839aaf71a00a2c6a65"


def _hash(value: int) -> str:
    return f"0x{value:064x}"


def _log(block: int, name: str, payload: dict[str, object]) -> ChainLog:
    return ChainLog(CHAIN, CONTRACT, block, _hash(block), _hash(block * 100), 0, name, payload)


def _vector_events(index: int, vector: dict) -> list[ChainLog]:
    """Build the lifecycle event stream that puts a fresh market in the vector's stored state."""
    market_id = 100 + index
    key = "0x" + f"{index + 1:064x}"
    state = vector["storedState"]
    deadline = vector["tradingDeadline"]
    block = index * 10 + 1
    events = [
        _log(block, "FixtureRegistered", {
            "fixture_key": key, "registrar": WALLET,
            "data": {"provider_id": "manual"}, "revision_hash": _hash(index + 1),
        }),
    ]
    block += 1
    if state == "CLOSED" and "early" in vector["name"]:
        # closeTrading before the deadline shortens it; the MarketClosed event carries
        # the shortened value the API must report.
        events.append(_log(block, "MarketCreated", {
            "market_id": market_id, "creator": WALLET, "question": f"Vector {index}?",
            "trading_deadline": deadline + 3_600, "fixture_key": key,
        }))
        events.append(_log(block + 1, "MarketClosed", {
            "market_id": market_id, "trading_deadline": deadline,
            "caller": WALLET, "evidence_hash": _hash(index + 2),
        }))
    else:
        events.append(_log(block, "MarketCreated", {
            "market_id": market_id, "creator": WALLET, "question": f"Vector {index}?",
            "trading_deadline": deadline, "fixture_key": key,
        }))
        if state == "CLOSED":
            # Closed at or after the deadline: the stored deadline is unchanged.
            events.append(_log(block + 1, "MarketClosed", {
                "market_id": market_id, "trading_deadline": deadline,
                "caller": WALLET, "evidence_hash": _hash(index + 2),
            }))
        elif state == "FINALIZED":
            events.append(_log(block + 1, "OutcomeProposed", {
                "market_id": market_id, "proposer": WALLET, "outcome": 0,
                "evidence_hash": _hash(index + 2),
                "evidence_uri": "https://example.invalid/vector",
                "challenge_deadline": deadline + 86_400,
            }))
            events.append(_log(block + 2, "MarketFinalized", {
                "market_id": market_id, "outcome": 0, "remaining_liability": 0,
            }))
        elif state == "VOID":
            events.append(_log(block + 1, "OutcomeProposed", {
                "market_id": market_id, "proposer": WALLET, "outcome": 2,
                "evidence_hash": _hash(index + 2),
                "evidence_uri": "https://example.invalid/vector",
                "challenge_deadline": deadline + 86_400,
            }))
            events.append(_log(block + 2, "MarketVoided", {
                "market_id": market_id, "remaining_liability": 0,
            }))
    return events


class Provider:
    def __init__(self, logs: list[ChainLog]) -> None:
        self.logs = logs

    def latest_block(self) -> int:
        return max(log.block_number for log in self.logs)

    def block_hash(self, block_number: int) -> str:
        return _hash(block_number)

    def get_logs(self, _address: str, start: int, end: int) -> list[ChainLog]:
        return [log for log in self.logs if start <= log.block_number <= end]


@pytest.fixture()
def client_and_session(tmp_path: Path) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'deadline-vectors.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_session() -> Generator[Session, None, None]:
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal
    app.dependency_overrides.clear()


def test_api_reports_raw_stored_state_and_deadline_for_every_vector(client_and_session) -> None:
    client, SessionLocal = client_and_session
    vectors = json.loads(VECTORS.read_text(encoding="utf-8"))["vectors"]

    logs: list[ChainLog] = []
    for index, vector in enumerate(vectors):
        logs.extend(_vector_events(index, vector))
    with SessionLocal() as session:
        service = EventIndexer(Provider(logs), IndexerConfig(
            chain_id=CHAIN, contract_address=CONTRACT, deployment_block=1,
            confirmation_depth=0, m4_enabled=True, abi_version="m4",
        ))
        service.sync_once(session)

    for index, vector in enumerate(vectors):
        response = client.get(f"/api/v2/markets/{100 + index}")
        assert response.status_code == 200, vector["name"]
        data = response.json()["data"]
        # Raw stored state: an expired OPEN market is still OPEN, terminal states are
        # FINALIZED/VOID, and nothing derives a phase here.
        assert data["state"] == vector["storedState"], vector["name"]
        # The stored deadline matches the vector: creation-time value, or the shortened
        # post-close value when a registrar early closed the market.
        returned = datetime.fromisoformat(data["trading_deadline"])
        assert returned == datetime.fromtimestamp(vector["tradingDeadline"], UTC), vector["name"]
        # Tradability is the frontend's derivation; the API exposes no second authority.
        assert "tradable" not in data and "phase" not in data, vector["name"]
