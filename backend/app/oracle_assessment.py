"""Deterministic, non-authoritative classification of imported result observations."""

from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import Fixture, FixtureResultObservation, OracleResultAssessment


class ResultAssessmentError(ValueError):
    pass


def classify_result(fixture: Fixture, observation: FixtureResultObservation) -> str:
    """Map Team A/B to YES/NO; canceled, tied and unsupported results to VOID."""
    if observation.match_status == "completed":
        if observation.winner_team_id == fixture.team_a_id:
            return "YES"
        if observation.winner_team_id == fixture.team_b_id:
            return "NO"
        raise ResultAssessmentError("completed result does not name a fixture team")
    if observation.match_status in {"canceled", "tied", "no_contest", "unsupported"}:
        if observation.winner_team_id is not None:
            raise ResultAssessmentError("VOID-type result must not name a winner")
        return "VOID"
    raise ResultAssessmentError("unsupported result status")


def assess_imported_results(session: Session, *, now: datetime | None = None) -> int:
    """Create one immutable assessment per observation; caller commits.

    This is safe to retry. A correction records a new assessment and flags changed
    outcomes for the challenge workflow; it never alters a prior proposal.
    """
    now = now or datetime.now(UTC)
    observations = session.scalars(
        select(FixtureResultObservation)
        .order_by(FixtureResultObservation.fixture_id, FixtureResultObservation.source_updated_at, FixtureResultObservation.id)
    ).all()
    count = 0
    for observation in observations:
        if session.scalar(select(OracleResultAssessment.id).where(
            OracleResultAssessment.observation_id == observation.id
        )) is not None:
            continue
        fixture = session.get(Fixture, observation.fixture_id)
        if fixture is None:
            raise ResultAssessmentError("result references missing fixture")
        outcome = classify_result(fixture, observation)
        previous = session.scalar(
            select(OracleResultAssessment)
            .join(FixtureResultObservation, OracleResultAssessment.observation_id == FixtureResultObservation.id)
            .where(OracleResultAssessment.fixture_id == fixture.id)
            .where(or_(
                FixtureResultObservation.source_updated_at < observation.source_updated_at,
                and_(FixtureResultObservation.source_updated_at == observation.source_updated_at,
                     FixtureResultObservation.id < observation.id),
            ))
            .order_by(FixtureResultObservation.source_updated_at.desc(), FixtureResultObservation.id.desc())
            .limit(1)
        )
        session.add(OracleResultAssessment(
            fixture_id=fixture.id,
            observation_id=observation.id,
            outcome=outcome,
            conflicts_with_prior=previous is not None and previous.outcome != outcome,
            assessed_at=now,
        ))
        session.flush()
        count += 1
    return count
