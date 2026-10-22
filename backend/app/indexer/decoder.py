from collections.abc import Sequence
import json
from pathlib import Path
from typing import Protocol

from eth_abi import decode
from eth_abi.exceptions import DecodingError
from eth_utils import keccak

from app.indexer.provider import ChainLog, EthereumLogProvider
from app.indexer.rpc import EthereumJsonRpcClient, RawEthereumLog, RpcResponseError


class LogDecoder(Protocol):
    def decode(self, chain_id: int, raw_log: RawEthereumLog) -> ChainLog | None: ...


class JsonAbiLogDecoder:
    REQUIRED_EVENTS = {
        "MarketCreated": [
            ("marketId", "uint256", True),
            ("creator", "address", True),
            ("question", "string", False),
            ("tradingDeadline", "uint256", False),
        ],
        "TradeExecuted": [
            ("marketId", "uint256", True),
            ("trader", "address", True),
            ("outcome", "uint8", True),
            ("shares", "uint256", False),
            ("cost", "uint256", False),
            ("yesQuantity", "uint256", False),
            ("noQuantity", "uint256", False),
        ],
    }

    def __init__(self, abi_path: str | Path) -> None:
        path = Path(abi_path)
        if not path.is_file():
            raise ValueError(f"ABI file does not exist: {path}")
        document = json.loads(path.read_text(encoding="utf-8"))
        abi = document.get("abi") if isinstance(document, dict) else document
        if not isinstance(abi, list):
            raise ValueError("ABI must be a JSON list or an object containing an abi list")
        self.events: dict[str, dict[str, object]] = {}
        by_name = {
            entry.get("name"): entry
            for entry in abi
            if isinstance(entry, dict) and entry.get("type") == "event"
        }
        for event_name, expected in self.REQUIRED_EVENTS.items():
            event = by_name.get(event_name)
            if not isinstance(event, dict) or not self._matches(event, expected):
                raise ValueError(f"ABI event {event_name} does not match the approved interface")
            signature = f"{event_name}({','.join(field[1] for field in expected)})"
            self.events["0x" + keccak(text=signature).hex()] = event

    def decode(self, chain_id: int, raw_log: RawEthereumLog) -> ChainLog | None:
        if not raw_log.topics:
            raise RpcResponseError("event log has no signature topic")
        event = self.events.get(raw_log.topics[0])
        if event is None:
            return None
        inputs = event["inputs"]
        indexed = [field for field in inputs if field["indexed"]]
        plain = [field for field in inputs if not field["indexed"]]
        if len(raw_log.topics) != len(indexed) + 1:
            raise RpcResponseError("event topic count does not match ABI")
        values: dict[str, object] = {}
        try:
            for field, topic in zip(indexed, raw_log.topics[1:], strict=True):
                values[field["name"]] = decode([field["type"]], bytes.fromhex(topic[2:]))[0]
            decoded_plain = decode(
                [field["type"] for field in plain], bytes.fromhex(raw_log.data[2:])
            )
        except (DecodingError, ValueError) as exc:
            raise RpcResponseError(f"could not decode {event['name']} event") from exc
        for field, value in zip(plain, decoded_plain, strict=True):
            values[field["name"]] = value
        payload = self._payload(str(event["name"]), values)
        return ChainLog(
            chain_id=chain_id,
            contract_address=raw_log.address,
            block_number=raw_log.block_number,
            block_hash=raw_log.block_hash,
            transaction_hash=raw_log.transaction_hash,
            log_index=raw_log.log_index,
            event_name=str(event["name"]),
            payload=payload,
        )

    @staticmethod
    def _matches(event: dict[str, object], expected: list[tuple[str, str, bool]]) -> bool:
        inputs = event.get("inputs")
        if not isinstance(inputs, list) or len(inputs) != len(expected):
            return False
        actual = [
            (field.get("name"), field.get("type"), field.get("indexed"))
            for field in inputs
            if isinstance(field, dict)
        ]
        return actual == expected

    @staticmethod
    def _payload(event_name: str, values: dict[str, object]) -> dict[str, object]:
        if event_name == "MarketCreated":
            return {
                "market_id": values["marketId"],
                "creator": values["creator"],
                "question": values["question"],
                "trading_deadline": values["tradingDeadline"],
            }
        return {
            "market_id": values["marketId"],
            "trader": values["trader"],
            "outcome": values["outcome"],
            "shares": values["shares"],
            "cost": values["cost"],
            "yes_quantity": values["yesQuantity"],
            "no_quantity": values["noQuantity"],
        }


class DecodingEthereumLogProvider(EthereumLogProvider):
    def __init__(self, rpc: EthereumJsonRpcClient, decoder: LogDecoder, chain_id: int) -> None:
        self.rpc = rpc
        self.decoder = decoder
        self.chain_id = chain_id

    def latest_block(self) -> int:
        return self.rpc.latest_block()

    def block_hash(self, block_number: int) -> str:
        return self.rpc.block_hash(block_number)

    def get_logs(self, contract_address: str, from_block: int, to_block: int) -> Sequence[ChainLog]:
        decoded = (
            self.decoder.decode(self.chain_id, raw_log)
            for raw_log in self.rpc.get_raw_logs(contract_address, from_block, to_block)
        )
        return [chain_log for chain_log in decoded if chain_log is not None]
