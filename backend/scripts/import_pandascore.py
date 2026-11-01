"""Operator-only PandaScore poll; requires an explicitly approved live-use setting."""

import argparse
import os

from app.fixture_service import import_document
from app.pandascore import GAME_PATH, PandaScoreClient, PandaScoreError


def main() -> int:
    parser = argparse.ArgumentParser(description="Import permitted PandaScore match data")
    parser.add_argument("game", choices=[*GAME_PATH, "all"])
    parser.add_argument("--max-pages", type=int, default=4)
    parser.add_argument("--validate-only", action="store_true", help="fetch and normalize without database writes")
    args = parser.parse_args()
    if os.getenv("PANDASCORE_USE_APPROVED", "").lower() != "true":
        parser.error("PANDASCORE_USE_APPROVED=true is required after team/provider-use review")
    token = os.getenv("PANDASCORE_API_TOKEN", "")
    if not token:
        parser.error("PANDASCORE_API_TOKEN is required")
    games = tuple(GAME_PATH) if args.game == "all" else (args.game,)
    try:
        with PandaScoreClient(token, max_pages=args.max_pages) as provider:
            documents = [provider.fetch(game) for game in games]
        if args.validate_only:
            for game, document in zip(games, documents, strict=True):
                print(f"{game}: {len(document.fixtures)} fixtures, {len(document.results)} results")
            return 0
        from app.database import SessionLocal

        with SessionLocal() as session:
            try:
                for game, document in zip(games, documents, strict=True):
                    counts = import_document(session, document)
                    print(f"{game}: {counts}")
                session.commit()
            except Exception:
                session.rollback()
                raise
        return 0
    except PandaScoreError as exc:
        parser.exit(2, f"PandaScore import failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
