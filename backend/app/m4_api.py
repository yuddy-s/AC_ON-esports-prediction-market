"""Read-only M4 projections. Solidity remains authoritative for current write eligibility."""

from datetime import UTC, datetime
from decimal import Decimal

from eth_utils import is_address
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.indexed_api import _active_contract, indexer_status
from app.models import IndexedMarket, IndexedMarketEvent, IndexedPosition


router = APIRouter(prefix="/api/v2", tags=["m4-indexed"])

TRADE_EVENTS = {"TradeExecuted", "SellExecuted"}
RESOLUTION_EVENTS = {
    "MarketClosed", "OutcomeProposed", "OutcomeChallenged", "ChallengeBondResolved",
    "ResolverSelectionRequested", "ResolverSelectionRequestFailed", "ResolverSelectionPending",
    "ResolverCommitteeSelected", "VRFFulfillmentIgnored", "ResolverVoteCast",
    "MarketFinalized", "MarketVoided",
}
CLAIM_EVENTS = {"PayoutClaimed", "CreatorSurplusWithdrawn"}


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _metadata(session: Session) -> dict[str, object]:
    status = indexer_status(session)
    return {
        "chain_id": status.chain_id,
        "contract_address": status.contract_address,
        "abi_version": status.abi_version,
        "safe_block": status.last_safe_block,
        "updated_at": _aware(status.updated_at),
        "authoritative": False,
    }


def _market_read(market: IndexedMarket) -> dict[str, object]:
    return {
        "market_id": market.market_id,
        "fixture_key": market.fixture_key,
        "question": market.question,
        "trading_deadline": _aware(market.trading_deadline),
        "state": market.state,
        "creator": market.creator,
        "yes_quantity": str(int(Decimal(market.yes_quantity))),
        "no_quantity": str(int(Decimal(market.no_quantity))),
        "final_outcome": market.final_outcome,
        "source_block_number": market.source_block_number,
        "source_transaction_hash": market.source_transaction_hash,
        "authoritative": False,
    }


def _event_read(event: IndexedMarketEvent) -> dict[str, object]:
    payload = dict(event.payload)
    amount_field = "cost" if event.event_name == "TradeExecuted" else "proceeds"
    return {
        "event": event.event_name,
        "kind": "BUY" if event.event_name == "TradeExecuted" else "SELL" if event.event_name == "SellExecuted" else event.event_name,
        "market_id": event.market_id,
        "actor": event.actor,
        "trader": payload.get("trader"),
        "outcome": int(payload["outcome"]) if "outcome" in payload else None,
        "shares": payload.get("shares"),
        "amount": payload.get(amount_field),
        "cost": payload.get("cost"),
        "proceeds": payload.get("proceeds"),
        "yes_quantity": payload.get("yes_quantity"),
        "no_quantity": payload.get("no_quantity"),
        "payload": payload,
        "block_number": event.block_number,
        "block_hash": event.block_hash,
        "transaction_hash": event.transaction_hash,
        "log_index": event.log_index,
        "authoritative": False,
    }


def _market_or_404(session: Session, market_id: int) -> tuple[object, IndexedMarket]:
    contract = _active_contract(session)
    market = None
    if contract is not None:
        market = session.scalar(select(IndexedMarket).where(
            IndexedMarket.chain_id == contract.chain_id,
            IndexedMarket.contract_address == contract.contract_address,
            IndexedMarket.market_id == market_id,
        ))
    if contract is None or market is None:
        raise HTTPException(status_code=404, detail="Indexed M4 market not found")
    return contract, market


@router.get("/indexer/status")
def m4_indexer_status(session: Session = Depends(get_session)) -> dict[str, object]:
    return indexer_status(session).model_dump()


@router.get("/markets")
def list_markets(
    state: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    contract = _active_contract(session)
    if contract is None:
        return {"items": [], "total": 0, "limit": limit, "offset": offset, "metadata": _metadata(session)}
    filters = [
        IndexedMarket.chain_id == contract.chain_id,
        IndexedMarket.contract_address == contract.contract_address,
        IndexedMarket.fixture_key.is_not(None),
    ]
    if state:
        filters.append(IndexedMarket.state == state.upper())
    total = session.scalar(select(func.count()).select_from(IndexedMarket).where(*filters)) or 0
    markets = session.scalars(select(IndexedMarket).where(*filters).order_by(IndexedMarket.market_id).offset(offset).limit(limit)).all()
    return {"items": [_market_read(m) for m in markets], "total": total, "limit": limit, "offset": offset, "metadata": _metadata(session)}


@router.get("/markets/{market_id}")
def get_market(market_id: int, session: Session = Depends(get_session)) -> dict[str, object]:
    _, market = _market_or_404(session, market_id)
    return {"data": _market_read(market), "metadata": _metadata(session)}


def _events_response(
    session: Session, market_id: int, names: set[str], limit: int, offset: int
) -> dict[str, object]:
    contract, _ = _market_or_404(session, market_id)
    filters = [
        IndexedMarketEvent.chain_id == contract.chain_id,
        IndexedMarketEvent.contract_address == contract.contract_address,
        IndexedMarketEvent.market_id == market_id,
        IndexedMarketEvent.event_name.in_(names),
    ]
    total = session.scalar(select(func.count()).select_from(IndexedMarketEvent).where(*filters)) or 0
    events = session.scalars(select(IndexedMarketEvent).where(*filters).order_by(
        IndexedMarketEvent.block_number, IndexedMarketEvent.log_index
    ).offset(offset).limit(limit)).all()
    return {"items": [_event_read(e) for e in events], "total": total, "limit": limit, "offset": offset, "metadata": _metadata(session)}


@router.get("/markets/{market_id}/history")
def market_history(market_id: int, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), session: Session = Depends(get_session)) -> dict[str, object]:
    return _events_response(session, market_id, TRADE_EVENTS, limit, offset)


@router.get("/markets/{market_id}/resolution")
def market_resolution(market_id: int, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0), session: Session = Depends(get_session)) -> dict[str, object]:
    return _events_response(session, market_id, RESOLUTION_EVENTS, limit, offset)


@router.get("/markets/{market_id}/claims")
def market_claims(market_id: int, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0), session: Session = Depends(get_session)) -> dict[str, object]:
    return _events_response(session, market_id, CLAIM_EVENTS, limit, offset)


@router.get("/portfolio/{wallet_address}")
def portfolio(wallet_address: str, session: Session = Depends(get_session)) -> dict[str, object]:
    if not is_address(wallet_address):
        raise HTTPException(status_code=422, detail="wallet_address must be a 20-byte Ethereum address")
    contract = _active_contract(session)
    normalized = wallet_address.lower()
    if contract is None:
        return {"wallet_address": normalized, "items": [], "metadata": _metadata(session)}
    positions = session.scalars(select(IndexedPosition).where(
        IndexedPosition.chain_id == contract.chain_id,
        IndexedPosition.contract_address == contract.contract_address,
        IndexedPosition.wallet_address == normalized,
    ).order_by(IndexedPosition.market_id)).all()
    items = []
    for position in positions:
        market = session.scalar(select(IndexedMarket).where(
            IndexedMarket.chain_id == contract.chain_id,
            IndexedMarket.contract_address == contract.contract_address,
            IndexedMarket.market_id == position.market_id,
        ))
        items.append({
            "market_id": position.market_id,
            "market": _market_read(market) if market else None,
            "yes_shares": str(int(Decimal(position.yes_shares))),
            "no_shares": str(int(Decimal(position.no_shares))),
            "claimed": position.claimed,
            "payout": str(int(Decimal(position.payout))),
            "updated_block_number": position.updated_block_number,
            "authoritative": False,
        })
    return {"wallet_address": normalized, "items": items, "metadata": _metadata(session)}
