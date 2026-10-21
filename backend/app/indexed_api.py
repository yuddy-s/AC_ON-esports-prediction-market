from datetime import UTC
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.config import get_settings
from app.models import IndexedContract, IndexedMarket, IndexedTrade, IndexerCheckpoint
from app.schemas import (
    IndexedMarketRead,
    IndexedTradeRead,
    IndexerStatusResponse,
    MarketListResponse,
    ProjectionMetadata,
    TradeListResponse,
    TransactionTradeLookupResponse,
)


router = APIRouter(prefix="/api")
settings = get_settings()


def _active_contract(session: Session) -> IndexedContract | None:
    return session.scalar(
        select(IndexedContract).where(IndexedContract.active.is_(True)).order_by(IndexedContract.id.desc())
    )


def _market_read(market: IndexedMarket) -> IndexedMarketRead:
    return IndexedMarketRead(
        market_id=market.market_id,
        question=market.question,
        trading_deadline=market.trading_deadline,
        state=market.state,
        creator=market.creator,
        yes_quantity=Decimal(market.yes_quantity),
        no_quantity=Decimal(market.no_quantity),
        projection=ProjectionMetadata(
            chain_id=market.chain_id,
            contract_address=market.contract_address,
            source_block_number=market.source_block_number,
            source_block_hash=market.source_block_hash,
            source_transaction_hash=market.source_transaction_hash,
            source_log_index=market.source_log_index,
        ),
    )


def _trade_read(trade: IndexedTrade) -> IndexedTradeRead:
    return IndexedTradeRead(
        market_id=trade.market_id,
        trader=trade.trader,
        outcome=trade.outcome,
        shares=Decimal(trade.shares),
        cost=Decimal(trade.cost),
        yes_quantity=Decimal(trade.yes_quantity),
        no_quantity=Decimal(trade.no_quantity),
        block_number=trade.block_number,
        block_hash=trade.block_hash,
        transaction_hash=trade.transaction_hash,
        log_index=trade.log_index,
    )


@router.get("/indexer/status", response_model=IndexerStatusResponse)
def indexer_status(session: Session = Depends(get_session)) -> IndexerStatusResponse:
    contract = _active_contract(session)
    if contract is None:
        return IndexerStatusResponse(
            configured=False,
            chain_id=settings.indexer_chain_id,
            contract_address=None,
            deployment_block=None,
            latest_observed_block=None,
            last_safe_block=None,
            next_block=None,
            lag_blocks=None,
            updated_at=None,
        )

    checkpoint = session.get(IndexerCheckpoint, contract.id)
    latest = checkpoint.latest_observed_block if checkpoint else None
    last_safe = checkpoint.last_safe_block if checkpoint else None
    lag = latest - last_safe if latest is not None and last_safe is not None else None
    updated_at = checkpoint.updated_at if checkpoint and latest is not None else None
    if updated_at is not None:
        # SQLite drops timezone information even for DateTime(timezone=True).
        updated_at = (
            updated_at.replace(tzinfo=UTC)
            if updated_at.tzinfo is None
            else updated_at.astimezone(UTC)
        )
    return IndexerStatusResponse(
        configured=True,
        chain_id=contract.chain_id,
        contract_address=contract.contract_address,
        deployment_block=contract.deployment_block,
        latest_observed_block=latest,
        last_safe_block=last_safe,
        next_block=checkpoint.next_block if checkpoint else contract.deployment_block,
        lag_blocks=lag,
        updated_at=updated_at,
    )


@router.get("/markets", response_model=MarketListResponse)
def list_markets(
    state: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> MarketListResponse:
    contract = _active_contract(session)
    if contract is None:
        return MarketListResponse(items=[], total=0, limit=limit, offset=offset)
    filters = [
        IndexedMarket.chain_id == contract.chain_id,
        IndexedMarket.contract_address == contract.contract_address,
    ]
    if state is not None:
        filters.append(IndexedMarket.state == state.upper())
    total = session.scalar(select(func.count()).select_from(IndexedMarket).where(*filters)) or 0
    statement = (
        select(IndexedMarket)
        .where(*filters)
        .order_by(IndexedMarket.market_id)
        .offset(offset)
        .limit(limit)
    )
    items = [_market_read(market) for market in session.scalars(statement).all()]
    return MarketListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/markets/{market_id}", response_model=IndexedMarketRead)
def get_market(market_id: int, session: Session = Depends(get_session)) -> IndexedMarketRead:
    contract = _active_contract(session)
    market = None
    if contract is not None:
        market = session.scalar(
            select(IndexedMarket).where(
                IndexedMarket.chain_id == contract.chain_id,
                IndexedMarket.contract_address == contract.contract_address,
                IndexedMarket.market_id == market_id,
            )
        )
    if market is None:
        raise HTTPException(status_code=404, detail="Indexed market not found")
    return _market_read(market)


@router.get("/markets/{market_id}/trades", response_model=TradeListResponse)
def list_market_trades(
    market_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> TradeListResponse:
    contract = _active_contract(session)
    market_exists = None
    if contract is not None:
        market_exists = session.scalar(
            select(IndexedMarket.id).where(
                IndexedMarket.chain_id == contract.chain_id,
                IndexedMarket.contract_address == contract.contract_address,
                IndexedMarket.market_id == market_id,
            )
        )
    if market_exists is None:
        raise HTTPException(status_code=404, detail="Indexed market not found")
    total = session.scalar(
        select(func.count()).select_from(IndexedTrade).where(
            IndexedTrade.chain_id == contract.chain_id,
            IndexedTrade.contract_address == contract.contract_address,
            IndexedTrade.market_id == market_id,
        )
    ) or 0
    statement = (
        select(IndexedTrade)
        .where(
            IndexedTrade.chain_id == contract.chain_id,
            IndexedTrade.contract_address == contract.contract_address,
            IndexedTrade.market_id == market_id,
        )
        .order_by(IndexedTrade.block_number, IndexedTrade.log_index)
        .offset(offset)
        .limit(limit)
    )
    items = [_trade_read(trade) for trade in session.scalars(statement).all()]
    return TradeListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/trades/by-transaction/{transaction_hash}", response_model=TransactionTradeLookupResponse)
def trades_by_transaction(
    transaction_hash: str = Path(pattern=r"^0x[0-9a-fA-F]{64}$"),
    session: Session = Depends(get_session),
) -> TransactionTradeLookupResponse:
    normalized_hash = transaction_hash.lower()
    contract = _active_contract(session)
    if contract is None:
        return TransactionTradeLookupResponse(transaction_hash=normalized_hash, items=[])

    statement = (
        select(IndexedTrade)
        .where(
            IndexedTrade.chain_id == contract.chain_id,
            IndexedTrade.contract_address == contract.contract_address,
            IndexedTrade.transaction_hash == normalized_hash,
        )
        .order_by(IndexedTrade.block_number, IndexedTrade.log_index)
    )
    items = [_trade_read(trade) for trade in session.scalars(statement).all()]
    return TransactionTradeLookupResponse(transaction_hash=normalized_hash, items=items)
