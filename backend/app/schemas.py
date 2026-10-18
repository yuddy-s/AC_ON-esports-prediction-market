from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    database: str
    message: str


class SampleMatchRead(BaseModel):
    slug: str
    game: str
    league: str
    team_a: str
    team_b: str
    start_time: datetime
    status: str
    market_label: str
    yes_price: Decimal
    no_price: Decimal
    source_note: str

    model_config = ConfigDict(from_attributes=True)
