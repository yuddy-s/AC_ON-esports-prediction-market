"""Read-only fixture catalog; source data is not a registered market."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Fixture, FixtureResultObservation


router = APIRouter(prefix="/api/fixtures", tags=["fixtures"])


class ResultObservationRead(BaseModel):
    id: int
    match_status: str
    winner_team_id: str | None
    source_updated_at: datetime
    evidence_url: str
    evidence_hash: str
    imported_at: datetime


class FixtureRead(BaseModel):
    id: int
    provider_id: str
    game_id: str
    external_match_id: str
    scheduled_start: datetime
    match_status: str
    team_a_id: str
    team_a_name: str
    team_b_id: str
    team_b_name: str
    evidence_url: str | None
    evidence_hash: str | None
    source_updated_at: datetime
    imported_at: datetime
    latest_result: ResultObservationRead | None
    authoritative: bool = False


class FixtureListResponse(BaseModel):
    items: list[FixtureRead]
    total: int
    limit: int
    offset: int


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _result_read(observation: FixtureResultObservation) -> ResultObservationRead:
    return ResultObservationRead(
        id=observation.id,
        match_status=observation.match_status,
        winner_team_id=observation.winner_team_id,
        source_updated_at=_aware(observation.source_updated_at),
        evidence_url=observation.evidence_url,
        evidence_hash=observation.evidence_hash,
        imported_at=_aware(observation.imported_at),
    )


def _fixture_read(session: Session, fixture: Fixture) -> FixtureRead:
    latest = session.scalar(
        select(FixtureResultObservation)
        .where(FixtureResultObservation.fixture_id == fixture.id)
        .order_by(FixtureResultObservation.source_updated_at.desc(), FixtureResultObservation.id.desc())
        .limit(1)
    )
    return FixtureRead(
        id=fixture.id,
        provider_id=fixture.provider_id,
        game_id=fixture.game_id,
        external_match_id=fixture.external_match_id,
        scheduled_start=_aware(fixture.scheduled_start),
        match_status=fixture.match_status,
        team_a_id=fixture.team_a_id,
        team_a_name=fixture.team_a_name,
        team_b_id=fixture.team_b_id,
        team_b_name=fixture.team_b_name,
        evidence_url=fixture.evidence_url,
        evidence_hash=fixture.evidence_hash,
        source_updated_at=_aware(fixture.source_updated_at),
        imported_at=_aware(fixture.imported_at),
        latest_result=_result_read(latest) if latest else None,
    )


@router.get("", response_model=FixtureListResponse)
def list_fixtures(
    game_id: str | None = None,
    match_status: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> FixtureListResponse:
    filters = []
    if game_id is not None:
        filters.append(Fixture.game_id == game_id)
    if match_status is not None:
        filters.append(Fixture.match_status == match_status)
    total = session.scalar(select(func.count()).select_from(Fixture).where(*filters)) or 0
    fixtures = session.scalars(
        select(Fixture).where(*filters).order_by(Fixture.scheduled_start, Fixture.id).offset(offset).limit(limit)
    ).all()
    return FixtureListResponse(
        items=[_fixture_read(session, fixture) for fixture in fixtures],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{fixture_id}", response_model=FixtureRead)
def get_fixture(fixture_id: int, session: Session = Depends(get_session)) -> FixtureRead:
    fixture = session.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Fixture not found")
    return _fixture_read(session, fixture)


@router.get("/{fixture_id}/results", response_model=list[ResultObservationRead])
def list_fixture_results(fixture_id: int, session: Session = Depends(get_session)) -> list[ResultObservationRead]:
    if session.get(Fixture, fixture_id) is None:
        raise HTTPException(status_code=404, detail="Fixture not found")
    observations = session.scalars(
        select(FixtureResultObservation)
        .where(FixtureResultObservation.fixture_id == fixture_id)
        .order_by(FixtureResultObservation.source_updated_at, FixtureResultObservation.id)
    ).all()
    return [_result_read(observation) for observation in observations]
