from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import SampleMatch


SAMPLE_MATCHES = [
    {
        "slug": "valorant-sentinels-loud",
        "game": "Valorant",
        "league": "VCT Americas",
        "team_a": "Sentinels",
        "team_b": "LOUD",
        "start_time": datetime(2026, 10, 3, 20, 0, tzinfo=UTC),
        "status": "OPEN",
        "market_label": "Will Sentinels beat LOUD?",
        "yes_price": 0.54,
        "no_price": 0.46,
        "source_note": "Fake Milestone 2 display data; not on-chain.",
    },
    {
        "slug": "lol-t1-geng",
        "game": "League of Legends",
        "league": "LCK Showcase",
        "team_a": "T1",
        "team_b": "Gen.G",
        "start_time": datetime(2026, 10, 5, 9, 30, tzinfo=UTC),
        "status": "OPEN",
        "market_label": "Will T1 beat Gen.G?",
        "yes_price": 0.49,
        "no_price": 0.51,
        "source_note": "Fake Milestone 2 display data; not on-chain.",
    },
    {
        "slug": "cs2-faze-navi",
        "game": "Counter-Strike 2",
        "league": "Demo Invitational",
        "team_a": "FaZe Clan",
        "team_b": "Natus Vincere",
        "start_time": datetime(2026, 10, 7, 18, 0, tzinfo=UTC),
        "status": "OPEN",
        "market_label": "Will FaZe Clan beat NAVI?",
        "yes_price": 0.57,
        "no_price": 0.43,
        "source_note": "Fake Milestone 2 display data; not on-chain.",
    },
]


def seed_sample_matches(session: Session) -> None:
    for row in SAMPLE_MATCHES:
        session.merge(SampleMatch(**row))
    session.commit()
