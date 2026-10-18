from collections.abc import Generator
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_collection.db")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_session
from app.main import app
from app.sample_data import seed_sample_matches


@pytest.fixture()
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    database_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as session:
        seed_sample_matches(session)

    def override_get_session() -> Generator[Session, None, None]:
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_reports_database_available(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "available"


def test_list_sample_matches_returns_seeded_rows(client: TestClient) -> None:
    response = client.get("/api/sample-matches")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    assert {match["slug"] for match in body} == {
        "valorant-sentinels-loud",
        "lol-t1-geng",
        "cs2-faze-navi",
    }
    assert all("not on-chain" in match["source_note"] for match in body)


def test_get_sample_match_by_slug(client: TestClient) -> None:
    response = client.get("/api/sample-matches/valorant-sentinels-loud")

    assert response.status_code == 200
    assert response.json()["team_a"] == "Sentinels"
    assert response.json()["team_b"] == "LOUD"


def test_unknown_sample_match_returns_404(client: TestClient) -> None:
    response = client.get("/api/sample-matches/not-real")

    assert response.status_code == 404
