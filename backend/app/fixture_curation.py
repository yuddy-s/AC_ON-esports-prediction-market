"""Operator-only approval of provider fixtures using independent evidence."""

from datetime import UTC, datetime
import hashlib
import json

from pydantic import HttpUrl, TypeAdapter
from sqlalchemy.orm import Session

from app.fixture_data import HASH_32
from app.models import Fixture, FixtureResultObservation, FixtureReviewEvent, ResultReviewEvent


def identity_hash(fixture: Fixture) -> str:
    start = fixture.scheduled_start
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    fields = {
        "provider_id": fixture.provider_id, "game_id": fixture.game_id,
        "external_match_id": fixture.external_match_id,
        "scheduled_start": start.astimezone(UTC).isoformat(),
        "team_a_id": fixture.team_a_id, "team_a_name": fixture.team_a_name,
        "team_b_id": fixture.team_b_id, "team_b_name": fixture.team_b_name,
    }
    return hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def review_fixture(session: Session, fixture_id: int, *, reviewer: str, approved: bool,
                   evidence_url: str | None = None, evidence_hash: str | None = None,
                   now: datetime | None = None) -> FixtureReviewEvent:
    """Persist an auditable decision; caller commits or rolls back."""
    fixture = session.get(Fixture, fixture_id, with_for_update=True)
    if fixture is None or fixture.provider_id != "pandascore":
        raise ValueError("PandaScore fixture not found")
    if not reviewer.strip() or len(reviewer) > 120:
        raise ValueError("reviewer identity is required")
    if approved:
        if not evidence_url or not evidence_hash or not HASH_32.fullmatch(evidence_hash):
            raise ValueError("independent evidence URL and 32-byte hash are required")
        url = TypeAdapter(HttpUrl).validate_python(evidence_url)
        if url.host == "api.pandascore.co":
            raise ValueError("PandaScore API response is not independent evidence")
        evidence_url = str(url)
        evidence_hash = evidence_hash.lower()
        fixture.curated_evidence_url = evidence_url
        fixture.curated_evidence_hash = evidence_hash
        fixture.curated_identity_hash = identity_hash(fixture)
    else:
        fixture.curated_evidence_url = None
        fixture.curated_evidence_hash = None
        fixture.curated_identity_hash = None
        evidence_url = evidence_hash = None
    event = FixtureReviewEvent(
        fixture_id=fixture.id, reviewer=reviewer.strip(), approved=approved,
        identity_hash=identity_hash(fixture), evidence_url=evidence_url,
        evidence_hash=evidence_hash, reviewed_at=now or datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    return event


def review_result(session: Session, observation_id: int, *, reviewer: str, approved: bool,
                  evidence_url: str | None = None, evidence_hash: str | None = None,
                  now: datetime | None = None) -> ResultReviewEvent:
    """Approve/revoke one exact observation; corrections require a fresh review."""
    observation = session.get(FixtureResultObservation, observation_id)
    fixture = session.get(Fixture, observation.fixture_id) if observation else None
    if fixture is None or fixture.provider_id != "pandascore":
        raise ValueError("PandaScore result observation not found")
    if not reviewer.strip() or len(reviewer) > 120:
        raise ValueError("reviewer identity is required")
    if approved:
        if not evidence_url or not evidence_hash or not HASH_32.fullmatch(evidence_hash):
            raise ValueError("independent evidence URL and 32-byte hash are required")
        url = TypeAdapter(HttpUrl).validate_python(evidence_url)
        if url.host == "api.pandascore.co":
            raise ValueError("PandaScore API response is not independent evidence")
        evidence_url = str(url)
        evidence_hash = evidence_hash.lower()
    else:
        evidence_url = evidence_hash = None
    event = ResultReviewEvent(
        observation_id=observation.id, reviewer=reviewer.strip(), approved=approved,
        evidence_url=evidence_url, evidence_hash=evidence_hash,
        reviewed_at=now or datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    return event
