"""Operator-only curation of an imported PandaScore fixture."""

import argparse

from app.database import SessionLocal
from app.fixture_curation import review_fixture


def main() -> int:
    parser = argparse.ArgumentParser(description="Approve or revoke a PandaScore fixture")
    parser.add_argument("fixture_id", type=int)
    parser.add_argument("--reviewer", required=True, help="operator identity for the audit record")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--approve", action="store_true")
    action.add_argument("--revoke", action="store_true")
    parser.add_argument("--evidence-url", help="independent organizer result or schedule source")
    parser.add_argument("--evidence-hash", help="0x-prefixed SHA-256 of reviewed evidence")
    args = parser.parse_args()
    if args.approve and (not args.evidence_url or not args.evidence_hash):
        parser.error("approval requires --evidence-url and --evidence-hash")
    with SessionLocal() as session:
        try:
            event = review_fixture(
                session, args.fixture_id, reviewer=args.reviewer, approved=args.approve,
                evidence_url=args.evidence_url, evidence_hash=args.evidence_hash,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
    print(f"fixture={event.fixture_id} review_event={event.id} approved={event.approved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
