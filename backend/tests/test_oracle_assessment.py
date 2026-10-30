from collections.abc import Generator
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_collection.db")

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.fixture_data import FixtureImportDocument, deterministic_mock
from app.fixture_service import import_document
from app.models import Fixture, FixtureResultObservation, OracleProposalEvent, OracleProposalIntent, OracleResultAssessment
from app.oracle_assessment import ResultAssessmentError, assess_imported_results, classify_result
from app.oracle_worker import (
    ClosedMarketRef, OracleGatewayUnavailable, OracleSubmissionUncertain,
    plan_proposal, process_proposal, run_oracle_once,
)


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


def test_stale_observation_does_not_replace_latest_result(session: Session) -> None:
    assess_imported_results(session)
    stale = deterministic_mock().model_dump(mode="json")
    stale["fixtures"] = []
    stale["results"][0]["winner_team_id"] = "bravo"
    stale["results"][0]["source_updated_at"] = "2030-01-01T20:00:00Z"
    stale["results"][0]["evidence_hash"] = "0x" + "33" * 32
    import_document(session, FixtureImportDocument.model_validate(stale))
    assess_imported_results(session)
    gateway = FakeOracleGateway()
    intent = plan_proposal(session, gateway.market, gateway, now=datetime(2030, 1, 2, tzinfo=UTC))
    assert intent is not None and intent.outcome == "YES"


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


class FakeOracleGateway:
    def __init__(self) -> None:
        self.market = ClosedMarketRef(11155111, "0x" + "12" * 20, 7, 1)
        self.state = "closed_unproposed"
        self.receipt = "pending"
        self.submit_calls = 0
        self.fail_before_submit = False
        self.uncertain_submit = False

    def closed_markets(self):
        return [self.market]

    def proposal_state(self, _market, _intent):
        return self.state

    def receipt_state(self, _transaction_hash):
        return self.receipt

    def submit(self, _intent):
        self.submit_calls += 1
        if self.fail_before_submit:
            raise OracleGatewayUnavailable("offline")
        if self.uncertain_submit:
            raise OracleSubmissionUncertain("unknown")
        return "0x" + "cd" * 32


def test_oracle_run_selects_observed_result_and_requires_chain_match(session: Session) -> None:
    gateway = FakeOracleGateway()
    now = datetime(2030, 1, 2, tzinfo=UTC)
    assert run_oracle_once(session, gateway, now=now) == 1
    session.commit()
    intent = session.scalar(select(OracleProposalIntent))
    assert intent is not None
    assert (intent.outcome, intent.evidence_hash, intent.status) == ("YES", "0x" + "11" * 32, "submitted")
    assert gateway.submit_calls == 1
    gateway.receipt = "success"
    run_oracle_once(session, gateway, now=now + timedelta(seconds=31))
    assert intent.status == "submitted" and gateway.submit_calls == 1
    gateway.state = "proposed_matching"
    run_oracle_once(session, gateway, now=now + timedelta(seconds=62))
    assert intent.status == "confirmed" and gateway.submit_calls == 1
    session.flush()
    assert [event.status for event in session.scalars(select(OracleProposalEvent).order_by(OracleProposalEvent.id))] == [
        "queued", "submitted", "submitted", "confirmed"
    ]


def test_correction_before_submission_pauses_oracle(session: Session) -> None:
    gateway = FakeOracleGateway()
    now = datetime(2030, 1, 2, tzinfo=UTC)
    assess_imported_results(session, now=now)
    intent = plan_proposal(session, gateway.market, gateway, now=now)
    assert intent is not None
    corrected = deterministic_mock().model_dump(mode="json")
    corrected["fixtures"] = []
    corrected["results"][0]["winner_team_id"] = "bravo"
    corrected["results"][0]["source_updated_at"] = "2030-01-01T22:00:00Z"
    corrected["results"][0]["evidence_hash"] = "0x" + "22" * 32
    import_document(session, FixtureImportDocument.model_validate(corrected))
    assess_imported_results(session, now=now)
    process_proposal(session, intent.id, gateway, now=now)
    assert intent.status == "correction_review"
    assert intent.outcome == "YES"
    assert intent.correction_observation_id is not None
    assert gateway.submit_calls == 0


def test_oracle_retries_only_pre_submission_failures(session: Session) -> None:
    gateway = FakeOracleGateway()
    gateway.fail_before_submit = True
    now = datetime(2030, 1, 2, tzinfo=UTC)
    run_oracle_once(session, gateway, now=now)
    intent = session.scalar(select(OracleProposalIntent))
    assert intent is not None and intent.status == "retryable_failure"
    gateway.fail_before_submit = False
    run_oracle_once(session, gateway, now=now + timedelta(seconds=31))
    assert intent.status == "submitted" and gateway.submit_calls == 2


def test_uncertain_oracle_submission_is_not_retried(session: Session) -> None:
    gateway = FakeOracleGateway()
    gateway.uncertain_submit = True
    now = datetime(2030, 1, 2, tzinfo=UTC)
    run_oracle_once(session, gateway, now=now)
    intent = session.scalar(select(OracleProposalIntent))
    assert intent is not None and intent.status == "submission_unknown"
    run_oracle_once(session, gateway, now=now + timedelta(hours=1))
    assert gateway.submit_calls == 1


def test_closed_market_gate_prevents_proposal(session: Session) -> None:
    gateway = FakeOracleGateway()
    gateway.state = "not_closed"
    run_oracle_once(session, gateway, now=datetime(2030, 1, 2, tzinfo=UTC))
    assert session.scalar(select(OracleProposalIntent)) is None
    assert gateway.submit_calls == 0


def test_correction_after_submission_is_retained_for_challenge(session: Session) -> None:
    gateway = FakeOracleGateway()
    now = datetime(2030, 1, 2, tzinfo=UTC)
    run_oracle_once(session, gateway, now=now)
    intent = session.scalar(select(OracleProposalIntent))
    assert intent is not None and intent.status == "submitted"
    corrected = deterministic_mock().model_dump(mode="json")
    corrected["fixtures"] = []
    corrected["results"][0]["winner_team_id"] = "bravo"
    corrected["results"][0]["source_updated_at"] = "2030-01-01T22:00:00Z"
    corrected["results"][0]["evidence_hash"] = "0x" + "22" * 32
    import_document(session, FixtureImportDocument.model_validate(corrected))
    gateway.state = "proposed_matching"
    run_oracle_once(session, gateway, now=now + timedelta(seconds=31))
    assert intent.status == "confirmed"
    assert intent.outcome == "YES"
    assert intent.correction_observation_id is not None
    assert gateway.submit_calls == 1
