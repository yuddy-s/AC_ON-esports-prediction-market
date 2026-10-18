from app.database import Base, SessionLocal, engine
from app.models import SampleMatch
from app.sample_data import seed_sample_matches


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_sample_matches(session)
    print("Seeded 3 fake sample matches.")


if __name__ == "__main__":
    main()
