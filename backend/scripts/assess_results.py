"""Operator-run, non-signing classification of imported result observations."""

from app.database import SessionLocal
from app.oracle_assessment import assess_imported_results


def main() -> None:
    with SessionLocal() as session:
        count = assess_imported_results(session)
        session.commit()
    print(f"Created {count} off-chain result assessments. No on-chain proposal was submitted.")


if __name__ == "__main__":
    main()
