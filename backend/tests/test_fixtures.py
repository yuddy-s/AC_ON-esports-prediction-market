from collections.abc import Generator
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_collection.db")

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_session
from app.fixture_data import FixtureImportDocument, deterministic_mock, load_manual_json
from app.fixture_service import FixtureImportError, import_document
from app.main import app
from app.models import Fixture, FixtureResultObservation


@pytest.fixture()
def session(tmp_path: Path) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'fixture.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as session:
        yield session
    engine.dispose()


def test_mock_import_is_idempotent_and_result_is_auditable(session: Session) -> None:
    document = deterministic_mock()
    first = import_document(session, document)
    session.commit()
    second = import_document(session, document)
    session.commit()

    assert (first.fixtures_created, first.results_created) == (1, 1)
    assert (second.fixtures_unchanged, second.results_unchanged) == (1, 1)
    assert session.scalar(select(func.count()).select_from(Fixture)) == 1
    assert session.scalar(select(func.count()).select_from(FixtureResultObservation)) == 1

    corrected = document.model_dump(mode="json")
    corrected["results"][0]["winner_team_id"] = "bravo"
    corrected["results"][0]["source_updated_at"] = "2030-01-01T22:00:00Z"
    corrected["results"][0]["evidence_hash"] = "0x" + "22" * 32
    counts = import_document(session, FixtureImportDocument.model_validate(corrected))
    session.commit()

    assert counts.results_created == 1
    assert [row.winner_team_id for row in session.scalars(
        select(FixtureResultObservation).order_by(FixtureResultObservation.source_updated_at)
    )] == ["alpha", "bravo"]


def test_manual_json_validates_before_import(tmp_path: Path) -> None:
    path = tmp_path / "matches.json"
    path.write_text(deterministic_mock().model_dump_json(), encoding="utf-8")
    assert load_manual_json(path).fixtures[0].provider_id == "acon-mock"

    malformed = deterministic_mock().model_dump(mode="json")
    malformed["results"][0]["evidence_hash"] = "not-a-hash"
    path.write_text(json.dumps(malformed), encoding="utf-8")
    with pytest.raises(ValidationError, match="evidence_hash"):
        load_manual_json(path)


def test_import_rejects_unknown_result_without_partial_commit(session: Session) -> None:
    document = deterministic_mock().model_dump(mode="json")
    document["results"][0]["external_match_id"] = "unknown"
    with pytest.raises(FixtureImportError, match="unknown fixture"):
        import_document(session, FixtureImportDocument.model_validate(document))
    session.rollback()
    assert session.scalar(select(func.count()).select_from(Fixture)) == 0


def test_import_rejects_stale_and_conflicting_fixture_updates(session: Session) -> None:
    original = deterministic_mock()
    import_document(session, original)
    session.commit()

    stale = original.model_dump(mode="json")
    stale["fixtures"][0]["source_updated_at"] = "2029-12-31T00:00:00Z"
    with pytest.raises(FixtureImportError, match="stale fixture"):
        import_document(session, FixtureImportDocument.model_validate(stale))
    session.rollback()

    conflicting = original.model_dump(mode="json")
    conflicting["fixtures"][0]["team_a_id"] = "other"
    with pytest.raises(FixtureImportError, match="conflicting fixture"):
        import_document(session, FixtureImportDocument.model_validate(conflicting))


def test_record_validation_rejects_ambiguous_teams_and_naive_times() -> None:
    document = deterministic_mock().model_dump(mode="json")
    document["fixtures"][0]["team_b_id"] = "alpha"
    document["fixtures"][0]["scheduled_start"] = "2030-01-01T18:00:00"
    with pytest.raises(ValidationError):
        FixtureImportDocument.model_validate(document)


def test_fixture_catalog_api_and_result_history(session: Session) -> None:
    import_document(session, deterministic_mock())
    session.commit()

    def override() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override
    try:
        with TestClient(app) as client:
            listing = client.get("/api/fixtures?game_id=valorant")
            assert listing.status_code == 200
            assert listing.json()["total"] == 1
            item = listing.json()["items"][0]
            assert item["authoritative"] is False
            assert item["latest_result"]["winner_team_id"] == "alpha"
            assert item["scheduled_start"].endswith("Z")
            assert client.get(f"/api/fixtures/{item['id']}/results").json()[0]["evidence_hash"] == "0x" + "11" * 32
            assert client.get("/api/fixtures?game_id=cs2").json()["total"] == 0
            assert client.get("/api/fixtures/999").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_fresh_sqlite_database_upgrades_through_fixture_migration(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    backend_dir = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "DATABASE_URL": f"sqlite+pysqlite:///{database_path}"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    engine = create_engine(f"sqlite+pysqlite:///{database_path}")
    with engine.connect() as connection:
        from sqlalchemy import inspect, text

        tables = set(inspect(connection).get_table_names())
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    engine.dispose()
    assert {"fixtures", "fixture_result_observations", "registration_challenges", "fixture_registration_jobs", "registration_job_events", "markets", "trades"} <= tables
    assert revision == "20261029_0003"


def test_existing_m3_contract_survives_fixture_migration(tmp_path: Path) -> None:
    from sqlalchemy import text

    database_path = tmp_path / "existing_m3.db"
    backend_dir = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "DATABASE_URL": f"sqlite+pysqlite:///{database_path}"}

    def upgrade(revision: str) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            cwd=backend_dir,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    upgrade("20261018_0001")
    engine = create_engine(f"sqlite+pysqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO indexed_contracts (chain_id, contract_address, deployment_block, abi_version, active) "
                 "VALUES (11155111, :address, 100, 'm3', 1)"),
            {"address": "0x" + "11" * 20},
        )
    upgrade("head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT abi_version FROM indexed_contracts")).scalar_one() == "m3"
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20261029_0003"
    engine.dispose()
