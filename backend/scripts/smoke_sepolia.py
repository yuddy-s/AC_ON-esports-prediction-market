"""Read-only live Sepolia-to-indexer-to-API smoke test for a completed handoff."""

import argparse
from datetime import UTC, datetime
from pathlib import Path

import httpx
from eth_utils import keccak

from app.config import get_settings
from app.indexer.decoder import DecodingEthereumLogProvider, JsonAbiLogDecoder
from app.indexer.handoff import DeploymentHandoff, ExampleTransaction, load_deployment_handoff
from app.indexer.provider import ChainLog
from app.indexer.rpc import EthereumJsonRpcClient, RpcError


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _read_json(api: httpx.Client, base_url: str, path: str) -> dict[str, object]:
    response = api.get(base_url.rstrip("/") + path)
    response.raise_for_status()
    body = response.json()
    _require(isinstance(body, dict), f"{path} did not return a JSON object")
    return body


def _event(
    provider: DecodingEthereumLogProvider,
    rpc: EthereumJsonRpcClient,
    address: str,
    example: ExampleTransaction,
    event_name: str,
    market_id: int,
) -> ChainLog:
    logs = provider.get_logs(address, example.block_number, example.block_number)
    matching = [
        log for log in logs
        if log.event_name == event_name
        and log.transaction_hash == example.transaction_hash
        and log.payload["market_id"] == market_id
    ]
    _require(len(matching) == 1, f"expected one {event_name} for the example transaction")
    event = matching[0]
    _require(event.contract_address.lower() == address.lower(), f"{event_name} came from another contract")
    _require(event.block_number == example.block_number, f"{event_name} came from another block")
    _require(event.block_hash == rpc.block_hash(example.block_number), f"{event_name} is not on the canonical block")
    return event


def verify_live_slice(
    handoff: DeploymentHandoff,
    rpc: EthereumJsonRpcClient,
    api: httpx.Client,
    api_base_url: str,
    *,
    max_status_age_seconds: int = 120,
    now: datetime | None = None,
) -> None:
    """Check public chain events against the confirmed API projection."""
    _require(rpc.chain_id() == handoff.chain_id, "RPC chain ID does not match the handoff")
    payment_token = rpc.call_address(
        handoff.market.address, "0x" + keccak(text="paymentToken()")[:4].hex()
    )
    _require(
        payment_token == handoff.token.address.lower(),
        "PredictionMarket.paymentToken() differs from the handoff ACON token address",
    )
    provider = DecodingEthereumLogProvider(rpc, JsonAbiLogDecoder(handoff.market.abi_path), handoff.chain_id)
    creation = _event(provider, rpc, handoff.market.address, handoff.creation, "MarketCreated", handoff.demo_market_id)
    trade = _event(provider, rpc, handoff.market.address, handoff.trade, "TradeExecuted", handoff.demo_market_id)

    health = _read_json(api, api_base_url, "/health")
    _require(health.get("status") == "ok", "API health is not ok")
    status = _read_json(api, api_base_url, "/api/indexer/status")
    _require(status.get("configured") is True, "API indexer is not configured")
    _require(status.get("authoritative") is False, "API indexer status lacks derived-state metadata")
    _require(status.get("chain_id") == handoff.chain_id, "API indexer chain ID differs from handoff")
    _require(
        isinstance(status.get("contract_address"), str)
        and status["contract_address"].lower() == handoff.market.address.lower(),
        "API indexer market address differs from handoff",
    )
    _require(
        isinstance(status.get("last_safe_block"), int)
        and status["last_safe_block"] >= handoff.trade.block_number,
        "API safe checkpoint has not reached the example trade",
    )
    updated_at = status.get("updated_at")
    _require(isinstance(updated_at, str), "API indexer has no freshness timestamp")
    try:
        observed_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("API indexer freshness timestamp is invalid") from exc
    _require(observed_at.tzinfo is not None, "API indexer freshness timestamp has no timezone")
    age_seconds = ((now or datetime.now(UTC)) - observed_at.astimezone(UTC)).total_seconds()
    _require(-60 <= age_seconds <= max_status_age_seconds, "API indexer observation is stale or in the future")

    market = _read_json(api, api_base_url, f"/api/markets/{handoff.demo_market_id}")
    _require(market.get("market_id") == handoff.demo_market_id, "API returned a different market")
    _require(market.get("question") == creation.payload["question"], "API market question differs from chain")
    _require(market.get("state") == "OPEN", "API market is not OPEN")
    deadline = market.get("trading_deadline")
    _require(isinstance(deadline, str), "API market has no trading deadline")
    try:
        deadline_time = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("API market trading deadline is invalid") from exc
    _require(deadline_time.tzinfo is not None, "API market trading deadline has no timezone")
    deadline_seconds = int(deadline_time.timestamp())
    _require(deadline_seconds == creation.payload["trading_deadline"], "API market deadline differs from chain")
    _require(
        isinstance(market.get("creator"), str)
        and market["creator"].lower() == str(creation.payload["creator"]).lower(),
        "API market creator differs from chain",
    )
    _require(
        int(market.get("yes_quantity", -1)) >= trade.payload["yes_quantity"]
        and int(market.get("no_quantity", -1)) >= trade.payload["no_quantity"],
        "API market quantities predate the example trade",
    )
    projection = market.get("projection")
    _require(isinstance(projection, dict), "API market has no projection metadata")
    _require(projection.get("authoritative") is False, "API market lacks derived-state metadata")
    _require(
        isinstance(projection.get("source_block_number"), int)
        and projection["source_block_number"] >= trade.block_number,
        "API market projection predates the example trade",
    )

    lookup = _read_json(api, api_base_url, f"/api/trades/by-transaction/{handoff.trade.transaction_hash}")
    _require(lookup.get("transaction_hash") == handoff.trade.transaction_hash, "API trade lookup returned another hash")
    items = lookup.get("items")
    _require(isinstance(items, list), "API trade lookup has no items list")
    matching = [item for item in items if isinstance(item, dict) and item.get("log_index") == trade.log_index]
    _require(len(matching) == 1, "API does not contain the example TradeExecuted log exactly once")
    item = matching[0]
    _require(
        item.get("market_id") == handoff.demo_market_id
        and item.get("transaction_hash") == trade.transaction_hash
        and item.get("block_hash") == trade.block_hash
        and item.get("block_number") == trade.block_number
        and item.get("authoritative") is False,
        "API trade identity or derived-state metadata differs from chain",
    )
    _require(
        isinstance(item.get("trader"), str)
        and item["trader"].lower() == str(trade.payload["trader"]).lower(),
        "API trade trader differs from chain",
    )
    for field in ("shares", "cost", "yes_quantity", "no_quantity"):
        _require(int(item.get(field, -1)) == trade.payload[field], f"API trade {field} differs from chain")
    _require(item.get("outcome") == trade.payload["outcome"], "API trade outcome differs from chain")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--max-status-age-seconds", type=int, default=120)
    args = parser.parse_args()
    if args.max_status_age_seconds < 1:
        parser.error("--max-status-age-seconds must be positive")
    rpc_url = get_settings().sepolia_rpc_url
    if not rpc_url:
        parser.error("SEPOLIA_RPC_URL must be set privately in the environment")
    try:
        handoff = load_deployment_handoff(args.manifest)
        rpc = EthereumJsonRpcClient(rpc_url)
        try:
            with httpx.Client(timeout=10) as api:
                verify_live_slice(
                    handoff, rpc, api, args.api_base_url,
                    max_status_age_seconds=args.max_status_age_seconds,
                )
        finally:
            rpc.close()
    except (ValueError, OSError, httpx.HTTPError, RpcError) as exc:
        print(f"Sepolia smoke test failed: {exc}")
        return 1
    print("Sepolia market creation, guarded buy, indexer, and API projections match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
