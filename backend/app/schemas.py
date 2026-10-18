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


class ProjectionMetadata(BaseModel):
    chain_id: int
    contract_address: str
    source_block_number: int
    source_block_hash: str
    source_transaction_hash: str
    source_log_index: int
    authoritative: bool = False


class IndexedMarketRead(BaseModel):
    market_id: int
    question: str
    trading_deadline: datetime
    state: str
    creator: str
    yes_quantity: Decimal
    no_quantity: Decimal
    projection: ProjectionMetadata


class IndexedTradeRead(BaseModel):
    market_id: int
    trader: str
    outcome: int
    shares: Decimal
    cost: Decimal
    yes_quantity: Decimal
    no_quantity: Decimal
    block_number: int
    block_hash: str
    transaction_hash: str
    log_index: int


class MarketListResponse(BaseModel):
    items: list[IndexedMarketRead]
    total: int
    limit: int
    offset: int


class TradeListResponse(BaseModel):
    items: list[IndexedTradeRead]
    total: int
    limit: int
    offset: int


class IndexerStatusResponse(BaseModel):
    configured: bool
    chain_id: int
    contract_address: str | None
    deployment_block: int | None
    latest_observed_block: int | None
    last_safe_block: int | None
    next_block: int | None
    lag_blocks: int | None
    authoritative: bool = False
