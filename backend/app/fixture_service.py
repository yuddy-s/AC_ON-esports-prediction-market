"""Transactional import of non-authoritative fixture and result source data."""

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.fixture_data import FixtureImportDocument, FixtureRecord, ResultRecord
from app.models import Fixture, FixtureRegistrationJob, FixtureResultObservation


class FixtureImportError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ImportCounts:
    fixtures_created: int = 0
    fixtures_updated: int = 0
    fixtures_unchanged: int = 0
    results_created: int = 0
    results_unchanged: int = 0


def _utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes even for DateTime(timezone=True).
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _fixture_values(record: FixtureRecord) -> dict[str, object]:
    values = record.model_dump()
    values["evidence_url"] = str(record.evidence_url) if record.evidence_url else None
    return values


def _same_fixture(fixture: Fixture, values: dict[str, object]) -> bool:
    return all(
        _utc(getattr(fixture, name)) == value if isinstance(value, datetime) else getattr(fixture, name) == value
        for name, value in values.items()
    )


def _result_hash(record: ResultRecord) -> str:
    canonical = json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def import_document(session: Session, document: FixtureImportDocument) -> ImportCounts:
    """Import a complete document atomically; caller commits or rolls back."""
    created = updated = unchanged = results_created = results_unchanged = 0
    for record in document.fixtures:
        values = _fixture_values(record)
        fixture = session.scalar(
            select(Fixture).where(
                Fixture.provider_id == record.provider_id,
                Fixture.game_id == record.game_id,
                Fixture.external_match_id == record.external_match_id,
            )
        )
        if fixture is None:
            session.add(Fixture(**values))
            session.flush()
            created += 1
            continue
        previous_update = _utc(fixture.source_updated_at)
        if record.source_updated_at < previous_update:
            raise FixtureImportError(f"stale fixture update: {record.identity}")
        if record.source_updated_at == previous_update:
            if not _same_fixture(fixture, values):
                raise FixtureImportError(f"conflicting fixture update at the same source time: {record.identity}")
            unchanged += 1
            continue
        registration = session.scalar(select(FixtureRegistrationJob).where(FixtureRegistrationJob.fixture_id == fixture.id))
        has_result = session.scalar(select(FixtureResultObservation.id).where(
            FixtureResultObservation.fixture_id == fixture.id
        )) is not None
        team_ids_changed = (record.team_a_id != fixture.team_a_id or record.team_b_id != fixture.team_b_id)
        if team_ids_changed and (has_result or (registration is not None and registration.status == "confirmed")):
            raise FixtureImportError(f"team mapping is frozen after a result or confirmed registration: {record.identity}")
        if registration is not None and registration.status == "confirmed" and record.scheduled_start != _utc(fixture.scheduled_start):
            raise FixtureImportError(f"scheduled start is frozen after confirmed registration: {record.identity}")
        for name, value in values.items():
            setattr(fixture, name, value)
        updated += 1
    session.flush()

    for record in document.results:
        fixture = session.scalar(
            select(Fixture).where(
                Fixture.provider_id == record.provider_id,
                Fixture.game_id == record.game_id,
                Fixture.external_match_id == record.external_match_id,
            )
        )
        if fixture is None:
            raise FixtureImportError(f"result references an unknown fixture: {record.identity}")
        if record.winner_team_id is not None and record.winner_team_id not in {fixture.team_a_id, fixture.team_b_id}:
            raise FixtureImportError(f"winner does not match the fixture teams: {record.identity}")
        fingerprint = _result_hash(record)
        existing = session.scalar(
            select(FixtureResultObservation.id).where(
                FixtureResultObservation.fixture_id == fixture.id,
                FixtureResultObservation.observation_hash == fingerprint,
            )
        )
        if existing is not None:
            results_unchanged += 1
            continue
        session.add(
            FixtureResultObservation(
                fixture_id=fixture.id,
                match_status=record.match_status,
                winner_team_id=record.winner_team_id,
                source_updated_at=record.source_updated_at,
                evidence_url=str(record.evidence_url),
                evidence_hash=record.evidence_hash,
                observation_hash=fingerprint,
            )
        )
        session.flush()
        results_created += 1

    return ImportCounts(created, updated, unchanged, results_created, results_unchanged)
