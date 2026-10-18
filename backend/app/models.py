from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SampleMatch(Base):
    __tablename__ = "sample_matches"

    slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    game: Mapped[str] = mapped_column(String(80), nullable=False)
    league: Mapped[str] = mapped_column(String(120), nullable=False)
    team_a: Mapped[str] = mapped_column(String(120), nullable=False)
    team_b: Mapped[str] = mapped_column(String(120), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    market_label: Mapped[str] = mapped_column(String(160), nullable=False)
    yes_price: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    no_price: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    source_note: Mapped[str] = mapped_column(Text, nullable=False)
