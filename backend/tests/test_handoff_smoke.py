from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path

from eth_abi import encode
from eth_utils import keccak, to_checksum_address
import httpx
import pytest

from app.indexer.handoff import load_deployment_handoff
from app.indexer.rpc import RawEthereumLog
from scripts.smoke_sepolia import verify_live_slice


SOURCE_COMMIT = "a" * 40
TOKEN_ADDRESS = to_checksum_address("0x" + "a1" * 20)
MARKET_ADDRESS = to_checksum_address("0x" + "b2" * 20)
CREATOR = to_checksum_address("0x" + "c3" * 20)
TRADER = to_checksum_address("0x" + "d4" * 20)
NOW = datetime(2026, 10, 21, 18, 0, tzinfo=UTC)


def _hash(value: int) -> str:
    return f"0x{value:064x}"


def _function(name: str, inputs: list[str], outputs: list[str]) -> dict[str, object]:
    return {
        "type": "function", "name": name,
        "inputs": [{"type": item} for item in inputs],
        "outputs": [{"type": item} for item in outputs],
    }


def _token_abi() -> list[dict[str, object]]:
    return [
        _function("faucet", [], ["uint256"]),
        _function("approve", ["address", "uint256"], ["bool"]),
        _function("balanceOf", ["address"], ["uint256"]),
        _function("allowance", ["address", "address"], ["uint256"]),
        _function("hasClaimedFaucet", ["address"], ["bool"]),
        _function("decimals", [], ["uint8"]),
    ]


def _market_abi() -> list[dict[str, object]]:
    return [
        *_approved_events(),
        _function("paymentToken", [], ["address"]),
        _function("marketCount", [], ["uint256"]),
        _function("createMarket", ["string", "uint256"], ["uint256"]),
        _function("getMarket", ["uint256"], ["string", "uint256", "uint8", "address", "uint256", "uint256"]),
        _function("quoteBuy", ["uint256", "uint8", "uint256"], ["uint256"]),
        _function("buy", ["uint256", "uint8", "uint256", "uint256"], ["uint256"]),
        _function("balanceOf", ["uint256", "address", "uint8"], ["uint256"]),
    ]


def _approved_events() -> list[dict[str, object]]:
    return [
        {
            "type": "event", "name": "MarketCreated",
            "inputs": [
                {"name": "marketId", "type": "uint256", "indexed": True},
                {"name": "creator", "type": "address", "indexed": True},
                {"name": "question", "type": "string", "indexed": False},
                {"name": "tradingDeadline", "type": "uint256", "indexed": False},
            ],
        },
        {
            "type": "event", "name": "TradeExecuted",
            "inputs": [
                {"name": "marketId", "type": "uint256", "indexed": True},
                {"name": "trader", "type": "address", "indexed": True},
                {"name": "outcome", "type": "uint8", "indexed": True},
                {"name": "shares", "type": "uint256", "indexed": False},
                {"name": "cost", "type": "uint256", "indexed": False},
                {"name": "yesQuantity", "type": "uint256", "indexed": False},
                {"name": "noQuantity", "type": "uint256", "indexed": False},
            ],
        },
    ]


def _write_abi(root: Path, contract: str, abi: list[dict[str, object]]) -> tuple[str, str]:
    contents = json.dumps(abi).encode()
    digest = hashlib.sha256(contents).hexdigest()
    relative = f"deployments/abi/{contract}.{SOURCE_COMMIT[:12]}.{digest[:12]}.abi.json"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)
    return relative, digest


def _manifest(root: Path) -> tuple[Path, dict[str, object]]:
    token_path, token_digest = _write_abi(root, "ACONTestToken", _token_abi())
    market_path, market_digest = _write_abi(root, "PredictionMarket", _market_abi())
    document = {
        "manifest_version": 1,
        "network": "ethereum-sepolia",
        "chain_id": 11155111,
        "source_commit": SOURCE_COMMIT,
        "confirmation_depth": 2,
        "token": {
            "address": TOKEN_ADDRESS,
            "deployment_transaction_hash": _hash(10),
            "deployment_block": 10,
            "abi_path": token_path,
            "abi_sha256": token_digest,
        },
        "market": {
            "address": MARKET_ADDRESS,
            "deployment_transaction_hash": _hash(11),
            "deployment_block": 11,
            "abi_path": market_path,
            "abi_sha256": market_digest,
        },
        "demo": {
            "market_id": 0,
            "creation": {"transaction_hash": _hash(12), "block_number": 12},
            "trade": {"transaction_hash": _hash(13), "block_number": 13},
        },
    }
    path = root / "deployments" / "sepolia-m3.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path, document


def test_manifest_validates_exact_abi_digest_and_version(tmp_path: Path) -> None:
    path, document = _manifest(tmp_path)

    handoff = load_deployment_handoff(path, repo_root=tmp_path)

    assert handoff.market.address == MARKET_ADDRESS
    assert handoff.market.abi_version.startswith("PredictionMarket." + SOURCE_COMMIT[:12])
    assert handoff.trade.transaction_hash == _hash(13)
    (tmp_path / document["market"]["abi_path"]).write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="abi_sha256 does not match"):
        load_deployment_handoff(path, repo_root=tmp_path)


def test_manifest_rejects_wrong_chain_and_extra_secret_field(tmp_path: Path) -> None:
    path, document = _manifest(tmp_path)
    document["chain_id"] = 1
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Ethereum Sepolia"):
        load_deployment_handoff(path, repo_root=tmp_path)

    document["chain_id"] = 11155111
    document["rpc_url"] = "must-not-be-committed"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest must have exactly"):
        load_deployment_handoff(path, repo_root=tmp_path)


def test_manifest_rejects_abi_missing_frontend_market_function(tmp_path: Path) -> None:
    path, document = _manifest(tmp_path)
    incomplete = [entry for entry in _market_abi() if entry.get("name") != "getMarket"]
    abi_path, digest = _write_abi(tmp_path, "PredictionMarket", incomplete)
    document["market"]["abi_path"] = abi_path
    document["market"]["abi_sha256"] = digest
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="missing function getMarket"):
        load_deployment_handoff(path, repo_root=tmp_path)


class FakeRpc:
    def chain_id(self) -> int:
        return 11155111

    def block_hash(self, block_number: int) -> str:
        return _hash(block_number)

    def get_raw_logs(self, _address: str, from_block: int, _to_block: int) -> list[RawEthereumLog]:
        if from_block == 12:
            return [RawEthereumLog(
                address=MARKET_ADDRESS.lower(), block_number=12, block_hash=_hash(12),
                transaction_hash=_hash(12), log_index=0,
                topics=(
                    "0x" + keccak(text="MarketCreated(uint256,address,string,uint256)").hex(),
                    "0x" + encode(["uint256"], [0]).hex(),
                    "0x" + encode(["address"], [CREATOR]).hex(),
                ),
                data="0x" + encode(["string", "uint256"], ["Will A win?", 1_900_000_000]).hex(),
            )]
        if from_block == 13:
            return [RawEthereumLog(
                address=MARKET_ADDRESS.lower(), block_number=13, block_hash=_hash(13),
                transaction_hash=_hash(13), log_index=2,
                topics=(
                    "0x" + keccak(text="TradeExecuted(uint256,address,uint8,uint256,uint256,uint256,uint256)").hex(),
                    "0x" + encode(["uint256"], [0]).hex(),
                    "0x" + encode(["address"], [TRADER]).hex(),
                    "0x" + encode(["uint8"], [0]).hex(),
                ),
                data="0x" + encode(["uint256"] * 4, [10**18, 5 * 10**17, 10**18, 0]).hex(),
            )]
        return []


def _api_handler(request: httpx.Request, *, stale: bool = False) -> httpx.Response:
    path = request.url.path
    if path == "/health":
        return httpx.Response(200, json={"status": "ok"})
    if path == "/api/indexer/status":
        return httpx.Response(200, json={
            "configured": True, "chain_id": 11155111, "contract_address": MARKET_ADDRESS.lower(),
            "last_safe_block": 15, "authoritative": False,
            "updated_at": (NOW - timedelta(hours=1) if stale else NOW).isoformat(),
        })
    if path == "/api/markets/0":
        return httpx.Response(200, json={
            "market_id": 0, "question": "Will A win?", "state": "OPEN",
            "trading_deadline": datetime.fromtimestamp(1_900_000_000, UTC).isoformat(),
            "creator": CREATOR.lower(), "yes_quantity": str(10**18), "no_quantity": "0",
            "projection": {"source_block_number": 13, "authoritative": False},
        })
    if path == f"/api/trades/by-transaction/{_hash(13)}":
        return httpx.Response(200, json={
            "transaction_hash": _hash(13),
            "items": [{
                "market_id": 0, "transaction_hash": _hash(13), "block_hash": _hash(13),
                "block_number": 13, "log_index": 2, "authoritative": False,
                "trader": TRADER.lower(), "outcome": 0, "shares": str(10**18),
                "cost": str(5 * 10**17), "yes_quantity": str(10**18), "no_quantity": "0",
            }],
        })
    return httpx.Response(404)


def test_smoke_test_compares_chain_events_with_api_projection(tmp_path: Path) -> None:
    path, _ = _manifest(tmp_path)
    handoff = load_deployment_handoff(path, repo_root=tmp_path)
    with httpx.Client(transport=httpx.MockTransport(_api_handler)) as api:
        verify_live_slice(handoff, FakeRpc(), api, "https://api.example", now=NOW)


def test_smoke_test_rejects_stale_worker_status(tmp_path: Path) -> None:
    path, _ = _manifest(tmp_path)
    handoff = load_deployment_handoff(path, repo_root=tmp_path)
    with httpx.Client(transport=httpx.MockTransport(lambda request: _api_handler(request, stale=True))) as api:
        with pytest.raises(ValueError, match="observation is stale"):
            verify_live_slice(handoff, FakeRpc(), api, "https://api.example", now=NOW)
