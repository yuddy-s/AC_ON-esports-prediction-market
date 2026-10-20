from app.database import SessionLocal, engine
from app.models import SampleMatch
from app.sample_data import seed_sample_matches


def main() -> None:
    SampleMatch.__table__.create(bind=engine, checkfirst=True)
    with SessionLocal() as session:
        seed_sample_matches(session)
    print("Seeded 3 fake sample matches.")


if __name__ == "__main__":
    main()
