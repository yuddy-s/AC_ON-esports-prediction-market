"""Operator-only PandaScore poll; requires an explicitly approved live-use setting."""

import argparse
from app.config import get_settings
from app.fixture_service import import_document
from app.pandascore import GAME_PATH, PandaScoreClient, PandaScoreError


def main() -> int:
    parser = argparse.ArgumentParser(description="Import permitted PandaScore match data")
    parser.add_argument("game", choices=[*GAME_PATH, "all"])
    parser.add_argument("--max-pages", type=int, default=4)
    parser.add_argument("--match-id", help="refresh one tracked PandaScore match (requires a single game)")
    parser.add_argument("--validate-only", action="store_true", help="fetch and normalize without database writes")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.pandascore_use_approved:
        parser.error("PANDASCORE_USE_APPROVED=true is required after team/provider-use review")
    if settings.pandascore_api_token is None:
        parser.error("PANDASCORE_API_TOKEN is required")
    token = settings.pandascore_api_token.get_secret_value()
    games = tuple(GAME_PATH) if args.game == "all" else (args.game,)
    if args.match_id and args.game == "all":
        parser.error("--match-id requires a single game")
    try:
        with PandaScoreClient(token, max_pages=args.max_pages) as provider:
            documents = [provider.fetch_match(game, args.match_id) if args.match_id else provider.fetch(game)
                         for game in games]
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
