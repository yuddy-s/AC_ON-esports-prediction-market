from collections.abc import Generator
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_collection.db")

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.fixture_data import FixtureImportDocument, deterministic_mock
from app.fixture_service import import_document
from app.models import Fixture, FixtureResultObservation, OracleResultAssessment
from app.oracle_assessment import ResultAssessmentError, assess_imported_results, classify_result


@pytest.fixture()
def session(tmp_path: Path) -> Generator[Session, None, None]:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'oracle.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as session:
        import_document(session, deterministic_mock())
        session.commit()
        yield session
    engine.dispose()


def test_assessments_are_idempotent_and_corrections_are_flagged(session: Session) -> None:
    assert assess_imported_results(session) == 1
    session.commit()
    assert assess_imported_results(session) == 0

    corrected = deterministic_mock().model_dump(mode="json")
    corrected["fixtures"] = []
    corrected["results"][0]["winner_team_id"] = "bravo"
    corrected["results"][0]["source_updated_at"] = "2030-01-01T22:00:00Z"
    corrected["results"][0]["evidence_hash"] = "0x" + "22" * 32
    import_document(session, FixtureImportDocument.model_validate(corrected))
    assert assess_imported_results(session) == 1
    session.commit()

    rows = session.scalars(select(OracleResultAssessment).order_by(OracleResultAssessment.id)).all()
    assert [(row.outcome, row.conflicts_with_prior) for row in rows] == [("YES", False), ("NO", True)]
    assert rows[0].outcome == "YES"  # correction did not rewrite the initial assessment


@pytest.mark.parametrize("status", ["canceled", "tied", "no_contest", "unsupported"])
def test_void_result_mapping(session: Session, status: str) -> None:
    fixture = session.get(Fixture, 1)
    observation = session.scalar(select(FixtureResultObservation))
    assert fixture is not None and observation is not None
    observation.match_status = status
    observation.winner_team_id = None
    assert classify_result(fixture, observation) == "VOID"


def test_rejects_ambiguous_completed_winner(session: Session) -> None:
    fixture = session.get(Fixture, 1)
    observation = session.scalar(select(FixtureResultObservation))
    assert fixture is not None and observation is not None
    observation.winner_team_id = "unrelated"
    with pytest.raises(ResultAssessmentError, match="does not name"):
        classify_result(fixture, observation)
