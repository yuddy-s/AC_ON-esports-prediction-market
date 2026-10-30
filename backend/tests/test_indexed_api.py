from collections.abc import Generator
from datetime import UTC, datetime
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_collection.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_session
from app.main import app
from app.models import IndexedContract, IndexedMarket, IndexedTrade, IndexerCheckpoint


CONTRACT = "0x1111111111111111111111111111111111111111"


@pytest.fixture()
def client_and_session(tmp_path: Path) -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'api.db'}",
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


def add_projection(SessionLocal: sessionmaker[Session]) -> None:
    with SessionLocal() as session:
        contract = IndexedContract(
            chain_id=11155111,
            contract_address=CONTRACT,
            deployment_block=100,
            abi_version="test",
            active=True,
        )
        session.add(contract)
        session.flush()
        session.add(
            IndexerCheckpoint(
                indexed_contract_id=contract.id,
                next_block=121,
                last_safe_block=120,
                last_safe_block_hash="0x" + "12" * 32,
                latest_observed_block=123,
                updated_at=datetime.now(UTC),
            )
        )
        for market_id in range(3):
            session.add(
                IndexedMarket(
                    chain_id=11155111,
                    contract_address=CONTRACT,
                    market_id=market_id,
                    question=f"Market {market_id}?",
                    trading_deadline=datetime.fromtimestamp(1_900_000_000 + market_id, UTC),
                    state="OPEN",
                    creator="0x2222222222222222222222222222222222222222",
                    yes_quantity=0,
                    no_quantity=0,
                    source_block_number=101 + market_id,
                    source_block_hash="0x" + f"{101 + market_id:064x}",
                    source_transaction_hash="0x" + f"{201 + market_id:064x}",
                    source_log_index=0,
                )
            )
        session.add(
            IndexedTrade(
                chain_id=11155111,
                contract_address=CONTRACT,
                market_id=0,
                trader="0x3333333333333333333333333333333333333333",
                outcome=1,
                shares=10**18,
                cost=5 * 10**17,
                yes_quantity=10**18,
                no_quantity=0,
                block_number=110,
                block_hash="0x" + f"{110:064x}",
                transaction_hash="0x" + f"{210:064x}",
                log_index=0,
            )
        )
        session.commit()


def test_empty_projection_endpoints(client_and_session: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = client_and_session

    status = client.get("/api/indexer/status")
    markets = client.get("/api/markets")

    assert status.status_code == 200
    assert status.json()["configured"] is False
    assert status.json()["abi_version"] is None
    assert status.json()["authoritative"] is False
    assert status.json()["updated_at"] is None
    assert markets.status_code == 200
    assert markets.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_market_pagination_and_projection_metadata(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, SessionLocal = client_and_session
    add_projection(SessionLocal)

    response = client.get("/api/markets?limit=1&offset=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert body["items"][0]["market_id"] == 1
    assert body["items"][0]["projection"]["authoritative"] is False
    assert body["items"][0]["projection"]["chain_id"] == 11155111


def test_market_detail_trade_history_and_indexer_lag(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, SessionLocal = client_and_session
    add_projection(SessionLocal)

    market = client.get("/api/markets/0")
    trades = client.get("/api/markets/0/trades?limit=10&offset=0")
    status = client.get("/api/indexer/status")

    assert market.status_code == 200
    assert market.json()["question"] == "Market 0?"
    assert trades.status_code == 200
    assert trades.json()["total"] == 1
    assert trades.json()["items"][0]["shares"] == "1000000000000000000"
    assert trades.json()["items"][0]["authoritative"] is False
    assert status.json()["configured"] is True
    assert status.json()["abi_version"] == "test"
    assert status.json()["lag_blocks"] == 3
    assert status.json()["next_block"] == 121
    assert status.json()["updated_at"] is not None


def test_missing_market_returns_404(client_and_session: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = client_and_session

    assert client.get("/api/markets/999").status_code == 404
    assert client.get("/api/markets/999/trades").status_code == 404


def test_pagination_validation(client_and_session: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = client_and_session

    assert client.get("/api/markets?limit=0").status_code == 422
    assert client.get("/api/markets?limit=101").status_code == 422
    assert client.get("/api/markets?offset=-1").status_code == 422


def test_market_state_filter_and_empty_page(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, SessionLocal = client_and_session
    add_projection(SessionLocal)

    filtered = client.get("/api/markets?state=open&limit=2&offset=2")
    empty = client.get("/api/markets?state=CLOSED")

    assert filtered.status_code == 200
    assert filtered.json()["total"] == 3
    assert [market["market_id"] for market in filtered.json()["items"]] == [2]
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["total"] == 0


def test_trade_history_pagination_validation_and_empty_page(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, SessionLocal = client_and_session
    add_projection(SessionLocal)
    with SessionLocal() as session:
        session.add(
            IndexedTrade(
                chain_id=11155111,
                contract_address=CONTRACT,
                market_id=0,
                trader="0x3333333333333333333333333333333333333333",
                outcome=0,
                shares=2 * 10**18,
                cost=10**18,
                yes_quantity=2 * 10**18,
                no_quantity=0,
                block_number=111,
                block_hash="0x" + f"{111:064x}",
                transaction_hash="0x" + f"{211:064x}",
                log_index=1,
            )
        )
        session.commit()

    page = client.get("/api/markets/0/trades?limit=1&offset=1")
    beyond = client.get("/api/markets/0/trades?limit=1&offset=2")
    other_market = client.get("/api/markets/1/trades")

    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert page.json()["items"][0]["block_number"] == 111
    assert page.json()["items"][0]["authoritative"] is False
    assert beyond.json()["items"] == []
    assert beyond.json()["total"] == 2
    assert other_market.json()["items"] == []
    assert other_market.json()["total"] == 0
    assert client.get("/api/markets/0/trades?limit=0").status_code == 422
    assert client.get("/api/markets/0/trades?limit=101").status_code == 422
    assert client.get("/api/markets/0/trades?offset=-1").status_code == 422


def test_status_exposes_old_observation_even_when_reported_lag_is_zero(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, SessionLocal = client_and_session
    add_projection(SessionLocal)
    with SessionLocal() as session:
        checkpoint = session.query(IndexerCheckpoint).one()
        checkpoint.latest_observed_block = 120
        checkpoint.updated_at = datetime(2020, 1, 1, tzinfo=UTC)
        session.commit()

    status = client.get("/api/indexer/status")

    assert status.status_code == 200
    assert status.json()["latest_observed_block"] == 120
    assert status.json()["last_safe_block"] == 120
    assert status.json()["lag_blocks"] == 0
    assert status.json()["updated_at"].startswith("2020-01-01T00:00:00")
    assert status.json()["updated_at"].endswith("Z")
    assert status.json()["authoritative"] is False


def test_transaction_lookup_is_empty_until_indexed_then_returns_all_matching_logs(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, SessionLocal = client_and_session
    add_projection(SessionLocal)
    transaction_hash = "0x" + f"{211:064x}"

    pending = client.get(f"/api/trades/by-transaction/{transaction_hash}")
    assert pending.status_code == 200
    assert pending.json() == {"transaction_hash": transaction_hash, "items": []}

    with SessionLocal() as session:
        for log_index in (0, 1):
            session.add(
                IndexedTrade(
                    chain_id=11155111,
                    contract_address=CONTRACT,
                    market_id=0,
                    trader="0x3333333333333333333333333333333333333333",
                    outcome=0,
                    shares=2 * 10**18,
                    cost=10**18,
                    yes_quantity=2 * 10**18,
                    no_quantity=0,
                    block_number=110,
                    block_hash="0x" + f"{110:064x}",
                    transaction_hash=transaction_hash,
                    log_index=log_index,
                )
            )
        session.commit()

    indexed = client.get(f"/api/trades/by-transaction/{transaction_hash.upper().replace('0X', '0x')}")
    assert indexed.status_code == 200
    body = indexed.json()
    assert body["transaction_hash"] == transaction_hash
    assert [item["log_index"] for item in body["items"]] == [0, 1]
    assert all(item["transaction_hash"] == transaction_hash for item in body["items"])
    assert all(item["authoritative"] is False for item in body["items"])


def test_transaction_lookup_validates_hash_and_scopes_active_contract(
    client_and_session: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, SessionLocal = client_and_session
    add_projection(SessionLocal)
    transaction_hash = "0x" + f"{210:064x}"

    assert client.get("/api/trades/by-transaction/0x1234").status_code == 422

    with SessionLocal() as session:
        session.add(
            IndexedContract(
                chain_id=11155111,
                contract_address="0x4444444444444444444444444444444444444444",
                deployment_block=200,
                abi_version="other",
                active=True,
            )
        )
        session.commit()

    response = client.get(f"/api/trades/by-transaction/{transaction_hash}")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_database_failure_reports_degraded_health_and_fails_indexed_reads() -> None:
    class BrokenSession:
        def execute(self, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError("simulated database outage")

        def scalar(self, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError("simulated database outage")

    def broken_session() -> Generator[BrokenSession, None, None]:
        yield BrokenSession()

    app.dependency_overrides[get_session] = broken_session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            health = client.get("/health")
            markets = client.get("/api/markets")
            status = client.get("/api/indexer/status")
            trades = client.get("/api/trades/by-transaction/0x" + "2" * 64)
    finally:
        app.dependency_overrides.clear()

    assert health.status_code == 200
    assert health.json()["status"] == "degraded"
    assert health.json()["database"] == "unavailable"
    assert markets.status_code == 500
    assert status.status_code == 500
    assert trades.status_code == 500
