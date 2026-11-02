import json
from pathlib import Path

from eth_abi import encode
from eth_utils import keccak
import httpx
import pytest

from app.indexer.decoder import JsonAbiEventDecoder, JsonAbiLogDecoder
from app.indexer.rpc import (
    EthereumJsonRpcClient,
    RawEthereumLog,
    RpcRangeTooLargeError,
    RpcResponseError,
)


ADDRESS = "0x" + "11" * 20
BLOCK_HASH = "0x" + "22" * 32
TX_HASH = "0x" + "33" * 32


def approved_abi() -> list[dict[str, object]]:
    return [{
        "type": "event",
        "name": "MarketCreated",
        "inputs": [
            {"name": "marketId", "type": "uint256", "indexed": True},
            {"name": "creator", "type": "address", "indexed": True},
            {"name": "question", "type": "string", "indexed": False},
            {"name": "tradingDeadline", "type": "uint256", "indexed": False},
        ],
    }, {
        "type": "event",
        "name": "TradeExecuted",
        "inputs": [
            {"name": "marketId", "type": "uint256", "indexed": True},
            {"name": "trader", "type": "address", "indexed": True},
            {"name": "outcome", "type": "uint8", "indexed": True},
            {"name": "shares", "type": "uint256", "indexed": False},
            {"name": "cost", "type": "uint256", "indexed": False},
            {"name": "yesQuantity", "type": "uint256", "indexed": False},
            {"name": "noQuantity", "type": "uint256", "indexed": False},
        ],
    }]


def rpc_client(handler, *, attempts: int = 3, sleeps: list[float] | None = None):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return EthereumJsonRpcClient(
        "https://rpc.example",
        client=client,
        max_attempts=attempts,
        sleep=(sleeps.append if sleeps is not None else lambda _seconds: None),
    )


def response(request: httpx.Request, result=None, error=None, status: int = 200) -> httpx.Response:
    request_body = json.loads(request.content)
    body = {"jsonrpc": "2.0", "id": request_body["id"]}
    body["error" if error is not None else "result"] = error if error is not None else result
    return httpx.Response(status, json=body)


def test_latest_block_retries_transient_http_failure() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return response(request, "0x2a")

    client = rpc_client(handler, sleeps=sleeps)

    assert client.latest_block() == 42
    assert calls == 2
    assert sleeps == [0.5]


def test_chain_id_uses_eth_chain_id() -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(json.loads(request.content)["method"])
        return response(request, "0xaa36a7")

    assert rpc_client(handler).chain_id() == 11155111
    assert methods == ["eth_chainId"]


def test_call_address_reads_strict_abi_encoded_eth_call_result() -> None:
    selector = "0x" + keccak(text="paymentToken()")[:4].hex()
    token_address = "0x" + "ab" * 20

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["method"] == "eth_call"
        assert body["params"] == [{"to": ADDRESS, "data": selector}, "latest"]
        return response(request, "0x" + "0" * 24 + token_address[2:])

    assert rpc_client(handler).call_address(ADDRESS, selector) == token_address


def test_call_address_rejects_malformed_abi_result() -> None:
    selector = "0x" + keccak(text="paymentToken()")[:4].hex()
    client = rpc_client(lambda request: response(request, "0x1234"))

    with pytest.raises(RpcResponseError, match="invalid ABI-encoded address"):
        client.call_address(ADDRESS, selector)


def test_log_range_is_split_when_provider_rejects_large_ranges() -> None:
    requested: list[tuple[int, int]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        params = body["params"][0]
        start, end = int(params["fromBlock"], 16), int(params["toBlock"], 16)
        requested.append((start, end))
        if end > start:
            return response(request, error={"code": -32005, "message": "block range too wide"})
        log = {
            "address": ADDRESS,
            "blockNumber": hex(start),
            "blockHash": BLOCK_HASH,
            "transactionHash": TX_HASH,
            "logIndex": "0x0",
            "topics": [BLOCK_HASH],
            "data": "0x",
        }
        return response(request, [log])

    logs = rpc_client(handler).get_raw_logs(ADDRESS, 1, 2)

    assert requested == [(1, 2), (1, 1), (2, 2)]
    assert [log.block_number for log in logs] == [1, 2]


def test_malformed_quantity_is_rejected() -> None:
    client = rpc_client(lambda request: response(request, "42"), attempts=1)

    with pytest.raises(RpcResponseError, match="invalid block number"):
        client.latest_block()


def test_nonretryable_http_error_is_not_retried() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401)

    with pytest.raises(RpcResponseError, match="401"):
        rpc_client(handler).latest_block()

    assert calls == 1


def test_invalid_json_is_rejected() -> None:
    client = rpc_client(lambda _request: httpx.Response(200, text="not-json"))

    with pytest.raises(RpcResponseError, match="invalid JSON"):
        client.latest_block()


def test_single_block_range_rejection_is_not_split_forever() -> None:
    client = rpc_client(
        lambda request: response(
            request, error={"code": -32005, "message": "block range too wide"}
        )
    )

    with pytest.raises(RpcRangeTooLargeError):
        client.get_raw_logs(ADDRESS, 7, 7)


def test_approved_market_event_is_decoded(tmp_path: Path) -> None:
    path = tmp_path / "abi.json"
    path.write_text(json.dumps(approved_abi()), encoding="utf-8")
    topic0 = "0x" + keccak(text="MarketCreated(uint256,address,string,uint256)").hex()
    raw = RawEthereumLog(
        address=ADDRESS,
        block_number=7,
        block_hash=BLOCK_HASH,
        transaction_hash=TX_HASH,
        log_index=0,
        topics=(topic0, "0x" + encode(["uint256"], [4]).hex(), "0x" + encode(["address"], [ADDRESS]).hex()),
        data="0x" + encode(["string", "uint256"], ["Will A win?", 1_900_000_000]).hex(),
    )

    decoded = JsonAbiLogDecoder(path).decode(11155111, raw)

    assert decoded is not None
    assert decoded.event_name == "MarketCreated"
    assert decoded.payload["market_id"] == 4
    assert decoded.payload["question"] == "Will A win?"


@pytest.mark.parametrize("event_name", ["MarketCreated", "TradeExecuted"])
def test_strict_decoder_ignores_overloaded_same_name_events(tmp_path: Path, event_name: str) -> None:
    if event_name == "MarketCreated":
        overload = {
            "type": "event",
            "name": event_name,
            "inputs": [
                {"name": "marketId", "type": "uint256", "indexed": True},
                {"name": "creator", "type": "address", "indexed": True},
                {"name": "opaque", "type": "bytes32", "indexed": False},
                {"name": "deadline", "type": "uint256", "indexed": False},
            ],
        }
        signature = "MarketCreated(uint256,address,bytes32,uint256)"
        topics = (
            "0x" + keccak(text=signature).hex(),
            "0x" + encode(["uint256"], [4]).hex(),
            "0x" + encode(["address"], [ADDRESS]).hex(),
        )
        data = "0x" + encode(["bytes32", "uint256"], [bytes.fromhex("44" * 32), 1_900_000_000]).hex()
    else:
        overload = {
            "type": "event",
            "name": event_name,
            "inputs": [
                {"name": "marketId", "type": "uint256", "indexed": True},
                {"name": "trader", "type": "address", "indexed": True},
                {"name": "outcome", "type": "uint8", "indexed": True},
                {"name": "opaque", "type": "bytes32", "indexed": False},
                {"name": "cost", "type": "uint256", "indexed": False},
                {"name": "yesQuantity", "type": "uint256", "indexed": False},
                {"name": "noQuantity", "type": "uint256", "indexed": False},
            ],
        }
        signature = "TradeExecuted(uint256,address,uint8,bytes32,uint256,uint256,uint256)"
        topics = (
            "0x" + keccak(text=signature).hex(),
            "0x" + encode(["uint256"], [4]).hex(),
            "0x" + encode(["address"], [ADDRESS]).hex(),
            "0x" + encode(["uint8"], [1]).hex(),
        )
        data = "0x" + encode(
            ["bytes32", "uint256", "uint256", "uint256"],
            [bytes.fromhex("44" * 32), 2 * 10**18, 3 * 10**18, 4 * 10**18],
        ).hex()

    # Put the overload first: a name-only allowlist used to overwrite its
    # lookup by name with the valid event while still admitting both topics.
    path = tmp_path / "abi-with-overload.json"
    path.write_text(json.dumps([overload, *approved_abi()]), encoding="utf-8")
    raw = RawEthereumLog(
        address=ADDRESS,
        block_number=7,
        block_hash=BLOCK_HASH,
        transaction_hash=TX_HASH,
        log_index=0,
        topics=topics,
        data=data,
    )

    assert JsonAbiLogDecoder(path).decode(11155111, raw) is None


def test_approved_trade_event_is_decoded(tmp_path: Path) -> None:
    path = tmp_path / "abi.json"
    path.write_text(json.dumps(approved_abi()), encoding="utf-8")
    topic0 = "0x" + keccak(
        text="TradeExecuted(uint256,address,uint8,uint256,uint256,uint256,uint256)"
    ).hex()
    raw = RawEthereumLog(
        address=ADDRESS,
        block_number=8,
        block_hash=BLOCK_HASH,
        transaction_hash=TX_HASH,
        log_index=2,
        topics=(
            topic0,
            "0x" + encode(["uint256"], [4]).hex(),
            "0x" + encode(["address"], [ADDRESS]).hex(),
            "0x" + encode(["uint8"], [1]).hex(),
        ),
        data="0x" + encode(
            ["uint256", "uint256", "uint256", "uint256"],
            [10**18, 2 * 10**18, 3 * 10**18, 4 * 10**18],
        ).hex(),
    )

    decoded = JsonAbiLogDecoder(path).decode(11155111, raw)

    assert decoded is not None
    assert decoded.event_name == "TradeExecuted"
    assert decoded.payload == {
        "market_id": 4,
        "trader": ADDRESS,
        "outcome": 1,
        "shares": 10**18,
        "cost": 2 * 10**18,
        "yes_quantity": 3 * 10**18,
        "no_quantity": 4 * 10**18,
    }


def test_decoder_rejects_nonapproved_abi(tmp_path: Path) -> None:
    path = tmp_path / "abi.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="MarketCreated"):
        JsonAbiLogDecoder(path)


def test_generic_decoder_supports_nested_tuple_event_fields(tmp_path: Path) -> None:
    components = [
        {"name": "providerId", "type": "string"},
        {"name": "gameId", "type": "string"},
        {"name": "externalMatchId", "type": "string"},
        {"name": "teamAId", "type": "string"},
        {"name": "teamBId", "type": "string"},
        {"name": "teamAName", "type": "string"},
        {"name": "teamBName", "type": "string"},
        {"name": "scheduledStart", "type": "uint256"},
        {"name": "evidenceHash", "type": "bytes32"},
        {"name": "evidenceURI", "type": "string"},
    ]
    abi = [{
        "type": "event",
        "name": "FixtureRegistered",
        "inputs": [
            {"name": "fixtureKey", "type": "bytes32", "indexed": True},
            {"name": "registrar", "type": "address", "indexed": True},
            {"name": "data", "type": "tuple", "components": components, "indexed": False},
            {"name": "revisionHash", "type": "bytes32", "indexed": False},
        ],
    }]
    path = tmp_path / "m4-candidate.abi.json"
    path.write_text(json.dumps(abi), encoding="utf-8")

    tuple_type = "(string,string,string,string,string,string,string,uint256,bytes32,string)"
    tuple_values = (
        "manual", "valorant", "match-1", "team-a", "team-b", "Alpha", "Bravo",
        1_900_000_000, bytes.fromhex("44" * 32), "https://example.test/match-1",
    )
    fixture_key = bytes.fromhex("55" * 32)
    revision_hash = bytes.fromhex("66" * 32)
    topic0 = "0x" + keccak(text=(
        "FixtureRegistered(bytes32,address,(string,string,string,string,string,string,string,uint256,bytes32,string),bytes32)"
    )).hex()
    raw = RawEthereumLog(
        address=ADDRESS,
        block_number=9,
        block_hash=BLOCK_HASH,
        transaction_hash=TX_HASH,
        log_index=3,
        topics=(
            topic0,
            "0x" + encode(["bytes32"], [fixture_key]).hex(),
            "0x" + encode(["address"], [ADDRESS]).hex(),
        ),
        data="0x" + encode([tuple_type, "bytes32"], [tuple_values, revision_hash]).hex(),
    )

    decoded = JsonAbiEventDecoder(path).decode(11155111, raw)

    assert decoded is not None
    assert decoded.event_name == "FixtureRegistered"
    assert decoded.payload["fixture_key"] == "0x" + fixture_key.hex()
    assert decoded.payload["registrar"] == ADDRESS.lower()
    assert decoded.payload["revision_hash"] == "0x" + revision_hash.hex()
    assert decoded.payload["data"] == {
        "provider_id": "manual",
        "game_id": "valorant",
        "external_match_id": "match-1",
        "team_a_id": "team-a",
        "team_b_id": "team-b",
        "team_a_name": "Alpha",
        "team_b_name": "Bravo",
        "scheduled_start": 1_900_000_000,
        "evidence_hash": "0x" + ("44" * 32),
        "evidence_uri": "https://example.test/match-1",
    }
