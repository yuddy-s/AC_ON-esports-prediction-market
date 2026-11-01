"""Operator-only review of one PandaScore result observation."""

import argparse

from app.database import SessionLocal
from app.fixture_curation import review_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Approve or revoke a PandaScore result observation")
    parser.add_argument("observation_id", type=int)
    parser.add_argument("--reviewer", required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--approve", action="store_true")
    action.add_argument("--revoke", action="store_true")
    parser.add_argument("--evidence-url")
    parser.add_argument("--evidence-hash")
    args = parser.parse_args()
    if args.approve and (not args.evidence_url or not args.evidence_hash):
        parser.error("approval requires independent --evidence-url and --evidence-hash")
    with SessionLocal() as session:
        try:
            event = review_result(
                session, args.observation_id, reviewer=args.reviewer, approved=args.approve,
                evidence_url=args.evidence_url, evidence_hash=args.evidence_hash,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
    print(f"observation={event.observation_id} review_event={event.id} approved={event.approved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
