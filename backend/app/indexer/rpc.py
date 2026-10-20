from collections.abc import Callable, Sequence
from dataclasses import dataclass
import logging
import re
import time
from typing import Any

import httpx


HEX_QUANTITY = re.compile(r"^0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)$")
HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")
ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
DATA = re.compile(r"^0x(?:[0-9a-fA-F]{2})*$")
logger = logging.getLogger("acon.indexer.rpc")


class RpcError(RuntimeError):
    pass


class RpcTransientError(RpcError):
    pass


class RpcRangeTooLargeError(RpcError):
    pass


class RpcResponseError(RpcError):
    pass


@dataclass(frozen=True, slots=True)
class RawEthereumLog:
    address: str
    block_number: int
    block_hash: str
    transaction_hash: str
    log_index: int
    topics: tuple[str, ...]
    data: str


class EthereumJsonRpcClient:
    def __init__(
        self,
        rpc_url: str,
        *,
        timeout_seconds: float = 10,
        max_attempts: int = 3,
        backoff_seconds: float = 0.5,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not rpc_url:
            raise ValueError("RPC URL is required")
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.client = client or httpx.Client(timeout=timeout_seconds)
        self.rpc_url = rpc_url
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.sleep = sleep
        self._request_id = 0

    def close(self) -> None:
        self.client.close()

    def latest_block(self) -> int:
        return self._quantity(self._request("eth_blockNumber", []), "block number")

    def block_hash(self, block_number: int) -> str:
        result = self._request("eth_getBlockByNumber", [hex(block_number), False])
        if not isinstance(result, dict) or not self._hash(result.get("hash")):
            raise RpcResponseError(f"missing block hash for block {block_number}")
        return str(result["hash"]).lower()

    def get_raw_logs(self, address: str, from_block: int, to_block: int) -> Sequence[RawEthereumLog]:
        if not ADDRESS.fullmatch(address):
            raise ValueError("contract address must be a 20-byte hex address")
        if from_block < 0 or to_block < from_block:
            raise ValueError("invalid block range")
        try:
            result = self._request(
                "eth_getLogs",
                [{"address": address, "fromBlock": hex(from_block), "toBlock": hex(to_block)}],
            )
        except RpcRangeTooLargeError:
            if from_block == to_block:
                raise
            midpoint = (from_block + to_block) // 2
            logger.warning("splitting rejected log range %s-%s at %s", from_block, to_block, midpoint)
            return [
                *self.get_raw_logs(address, from_block, midpoint),
                *self.get_raw_logs(address, midpoint + 1, to_block),
            ]
        if not isinstance(result, list):
            raise RpcResponseError("eth_getLogs result must be a list")
        return [self._raw_log(item) for item in result]

    def _request(self, method: str, params: list[object]) -> Any:
        self._request_id += 1
        request_id = self._request_id
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                response = self.client.post(self.rpc_url, json=payload)
                if response.status_code == 429 or response.status_code >= 500:
                    raise RpcTransientError(f"RPC HTTP {response.status_code}")
                if response.status_code >= 400:
                    raise RpcResponseError(f"RPC HTTP {response.status_code}")
                try:
                    body = response.json()
                except ValueError as exc:
                    raise RpcResponseError("RPC returned invalid JSON") from exc
                if not isinstance(body, dict) or body.get("id") != request_id:
                    raise RpcResponseError("malformed JSON-RPC response")
                if "error" in body:
                    self._raise_rpc_error(body["error"])
                if "result" not in body:
                    raise RpcResponseError("JSON-RPC response has no result")
                return body["result"]
            except (httpx.TimeoutException, httpx.TransportError, RpcTransientError) as exc:
                last_error = exc
                if attempt + 1 == self.max_attempts:
                    raise RpcTransientError(f"{method} failed after {self.max_attempts} attempts") from exc
                delay = self.backoff_seconds * (2**attempt)
                logger.warning("retrying RPC method=%s attempt=%s delay=%s", method, attempt + 2, delay)
                self.sleep(delay)
        raise RpcTransientError(f"{method} failed") from last_error

    @staticmethod
    def _raise_rpc_error(error: object) -> None:
        if not isinstance(error, dict):
            raise RpcResponseError("malformed JSON-RPC error")
        code = error.get("code")
        message = str(error.get("message", "JSON-RPC error"))
        lowered = message.lower()
        if code == -32005 or any(term in lowered for term in ("too many results", "block range", "range too wide")):
            raise RpcRangeTooLargeError(message)
        if code in {-32000, -32002, -32603}:
            raise RpcTransientError(message)
        raise RpcResponseError(f"JSON-RPC error {code}: {message}")

    @classmethod
    def _raw_log(cls, item: object) -> RawEthereumLog:
        if not isinstance(item, dict) or item.get("removed") is True:
            raise RpcResponseError("invalid or removed Ethereum log")
        address = item.get("address")
        block_hash = item.get("blockHash")
        transaction_hash = item.get("transactionHash")
        topics = item.get("topics")
        data = item.get("data")
        if not isinstance(address, str) or not ADDRESS.fullmatch(address):
            raise RpcResponseError("invalid log address")
        if not cls._hash(block_hash) or not cls._hash(transaction_hash):
            raise RpcResponseError("invalid log hash")
        if not isinstance(topics, list) or not topics or not all(cls._hash(topic) for topic in topics):
            raise RpcResponseError("invalid log topics")
        if not isinstance(data, str) or not DATA.fullmatch(data):
            raise RpcResponseError("invalid log data")
        return RawEthereumLog(
            address=address.lower(),
            block_number=cls._quantity(item.get("blockNumber"), "log block number"),
            block_hash=str(block_hash).lower(),
            transaction_hash=str(transaction_hash).lower(),
            log_index=cls._quantity(item.get("logIndex"), "log index"),
            topics=tuple(str(topic).lower() for topic in topics),
            data=data.lower(),
        )

    @staticmethod
    def _quantity(value: object, label: str) -> int:
        if not isinstance(value, str) or not HEX_QUANTITY.fullmatch(value):
            raise RpcResponseError(f"invalid {label}")
        return int(value, 16)

    @staticmethod
    def _hash(value: object) -> bool:
        return isinstance(value, str) and HASH.fullmatch(value) is not None
