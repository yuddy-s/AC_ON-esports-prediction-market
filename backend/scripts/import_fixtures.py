"""Operator-run import for M4 fixture and result JSON files.

Usage: python -m scripts.import_fixtures path/to/source.json [--validate-only]
"""

import argparse
from pathlib import Path

from pydantic import ValidationError

from app.fixture_data import load_manual_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and import M4 fixture/result source data")
    parser.add_argument("path", type=Path)
    parser.add_argument("--validate-only", action="store_true", help="parse and validate without using the database")
    args = parser.parse_args()
    try:
        document = load_manual_json(args.path)
        if args.validate_only:
            print(f"valid source document: {len(document.fixtures)} fixtures, {len(document.results)} results")
            return 0
        from app.database import SessionLocal
        from app.fixture_service import import_document

        with SessionLocal() as session:
            try:
                counts = import_document(session, document)
                session.commit()
            except Exception:
                session.rollback()
                raise
        print(
            f"fixtures created={counts.fixtures_created} updated={counts.fixtures_updated} "
            f"unchanged={counts.fixtures_unchanged}; results created={counts.results_created} "
            f"unchanged={counts.results_unchanged}"
        )
        return 0
    except (OSError, ValueError, ValidationError) as exc:
        parser.exit(2, f"fixture import failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
