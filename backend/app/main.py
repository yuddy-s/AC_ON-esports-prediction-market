from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, engine, get_session
from app.models import SampleMatch
from app.schemas import HealthResponse, SampleMatchRead

settings = get_settings()

app = FastAPI(
    title="AC_ON Backend",
    description="Milestone 2 FastAPI backend for non-authoritative sample match data.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health(session: Session = Depends(get_session)) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:
        return HealthResponse(
            status="degraded",
            database="unavailable",
            message=f"Backend is running, but database check failed: {exc}",
        )

    return HealthResponse(
        status="ok",
        database="available",
        message="Backend and database connection are healthy.",
    )


@app.get("/api/sample-matches", response_model=list[SampleMatchRead])
def list_sample_matches(session: Session = Depends(get_session)) -> list[SampleMatch]:
    statement = select(SampleMatch).order_by(SampleMatch.start_time)
    return list(session.scalars(statement).all())


@app.get("/api/sample-matches/{slug}", response_model=SampleMatchRead)
def get_sample_match(slug: str, session: Session = Depends(get_session)) -> SampleMatch:
    match = session.get(SampleMatch, slug)
    if match is None:
        raise HTTPException(status_code=404, detail="Sample match not found")
    return match


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
