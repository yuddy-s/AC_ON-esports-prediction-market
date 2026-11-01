from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.fixture_curation import review_fixture
from app.fixture_data import FixtureImportDocument
from app.fixture_service import import_document
from app.models import Fixture, FixtureResultObservation, FixtureReviewEvent
from app.pandascore import PandaScoreClient, PandaScoreError, PandaScoreRateLimited, normalize_match
from app.registration_service import RegistrationError, create_challenge


def match(match_id: int, *, status: str = "not_started", winner_id: int | None = None,
          modified_at: str = "2030-01-01T10:00:00Z", **changes: object) -> dict[str, object]:
    record = {
        "id": match_id, "status": status, "winner_id": winner_id,
        "scheduled_at": "2030-01-02T18:00:00Z", "modified_at": modified_at,
        "draw": False, "forfeit": False,
        "opponents": [
            {"type": "Team", "opponent": {"id": 10, "name": "Alpha"}},
            {"type": "Team", "opponent": {"id": 20, "name": "Bravo"}},
        ],
    }
    record.update(changes)
    return record


def client_for(handler, *, page_size: int = 2, max_pages: int = 2) -> PandaScoreClient:
    transport = httpx.MockTransport(handler)
    return PandaScoreClient("private-token", client=httpx.Client(transport=transport),
                            page_size=page_size, max_pages=max_pages)


def test_pages_all_three_games_and_keeps_token_in_header() -> None:
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, request.headers["Authorization"]))
        assert "token" not in str(request.url)
        page = request.url.params["page[number]"]
        if request.url.path.endswith("upcoming"):
            return httpx.Response(200, json=[match(1), match(2)] if page == "1" else [match(3)])
        return httpx.Response(200, json=[match(4, status="finished", winner_id=20,
                                               modified_at="2030-01-03T10:00:00Z")])

    provider = client_for(handler)
    for game, path in (("valorant", "valorant"), ("cs2", "csgo"), ("r6siege", "r6siege")):
        document = provider.fetch(game)
        assert len(document.fixtures) == 4
        assert len(document.results) == 1
        assert document.results[0].winner_team_id == "20"
        assert document.fixtures[0].game_id == game
        assert any(item[0] == f"/{path}/matches/upcoming" for item in seen)
    assert all(header == "Bearer private-token" for _, header in seen)


def test_ambiguous_results_and_incomplete_teams_are_not_proposals() -> None:
    assert normalize_match(match(1, opponents=[]), "valorant") is None
    assert normalize_match(match(1, opponents=[match(1)["opponents"][0]] * 2), "valorant") is None
    assert normalize_match(match(1, modified_at=None), "valorant") is None
    fixture, result = normalize_match(match(1, status="finished", winner_id=None), "valorant")
    assert fixture.match_status == "completed"
    assert result is None
    fixture, result = normalize_match(match(2, status="finished", draw=True), "valorant")
    assert result is not None and result.match_status == "tied"
    _, result = normalize_match(match(3, status="canceled", forfeit=True, winner_id=10), "valorant")
    assert result is None


def test_provider_errors_are_explicit() -> None:
    for status, expected in ((429, PandaScoreRateLimited), (401, PandaScoreError), (503, PandaScoreError)):
        provider = client_for(lambda _request: httpx.Response(status))
        with pytest.raises(expected):
            provider.fetch("cs2")
    provider = client_for(lambda _request: httpx.Response(200, json={"bad": "shape"}))
    with pytest.raises(PandaScoreError, match="match list"):
        provider.fetch("cs2")


def test_rate_budget_stops_before_second_page() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=[match(1), match(2)],
                              headers={"X-Rate-Limit-Remaining": "0"})

    with pytest.raises(PandaScoreRateLimited):
        client_for(handler).fetch("valorant")
    assert calls == 1


def test_import_is_idempotent_and_preserves_result_correction(tmp_path: Path) -> None:
    current = match(7, status="finished", winner_id=10,
                    modified_at="2030-01-03T10:00:00Z")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[] if request.url.path.endswith("upcoming") else [current])

    provider = client_for(handler)
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'provider.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as session:
        document = provider.fetch("r6siege")
        import_document(session, document)
        session.commit()
        again = import_document(session, provider.fetch("r6siege"))
        session.commit()
        assert again.fixtures_unchanged == 1 and again.results_unchanged == 1
        current["winner_id"] = 20
        current["modified_at"] = "2030-01-03T11:00:00Z"
        corrected = import_document(session, provider.fetch("r6siege"))
        session.commit()
        assert corrected.results_created == 1
        assert session.scalar(select(func.count()).select_from(Fixture)) == 1
        assert [row.winner_team_id for row in session.scalars(
            select(FixtureResultObservation).order_by(FixtureResultObservation.source_updated_at)
        )] == ["10", "20"]
    engine.dispose()


def test_provider_listing_cannot_bypass_registrar_curation(tmp_path: Path) -> None:
    provider = client_for(lambda request: httpx.Response(
        200, json=[match(9)] if request.url.path.endswith("upcoming") else []
    ))
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'curation.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, autoflush=False) as session:
        import_document(session, provider.fetch("valorant"))
        session.commit()
        with pytest.raises(RegistrationError) as exc:
            create_challenge(session, 1, "0x" + "11" * 20, 11155111,
                             "http://localhost:5173", now=datetime(2029, 12, 31, tzinfo=UTC))
        assert exc.value.code == "fixture_unreviewed"
        with pytest.raises(ValueError, match="independent"):
            review_fixture(session, 1, reviewer="operator", approved=True,
                           evidence_url="https://api.pandascore.co/matches/9",
                           evidence_hash="0x" + "ab" * 32)
        review_fixture(session, 1, reviewer="operator", approved=True,
                       evidence_url="https://organizer.example/match/9",
                       evidence_hash="0x" + "ab" * 32)
        session.commit()
        challenge, _nonce = create_challenge(
            session, 1, "0x" + "11" * 20, 11155111,
            "http://localhost:5173", now=datetime(2029, 12, 31, tzinfo=UTC),
        )
        assert challenge.fixture_snapshot["evidence_url"] == "https://organizer.example/match/9"
        assert session.scalar(select(func.count()).select_from(FixtureReviewEvent)) == 1

        changed = match(9, modified_at="2030-01-01T11:00:00Z",
                        scheduled_at="2030-01-03T18:00:00Z")
        fixture_record, _result = normalize_match(changed, "valorant")
        assert fixture_record is not None
        import_document(session, FixtureImportDocument(fixtures=[fixture_record]))
        session.commit()
        with pytest.raises(RegistrationError) as exc:
            create_challenge(session, 1, "0x" + "22" * 20, 11155111,
                             "http://localhost:5173", now=datetime(2029, 12, 31, tzinfo=UTC))
        assert exc.value.code == "fixture_unreviewed"

        review_fixture(session, 1, reviewer="operator", approved=False)
        session.commit()
        assert session.scalar(select(func.count()).select_from(FixtureReviewEvent)) == 2
    engine.dispose()
