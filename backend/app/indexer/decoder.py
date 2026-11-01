from collections.abc import Sequence
import json
from pathlib import Path
import re
from typing import Protocol

from eth_abi import decode
from eth_abi.exceptions import DecodingError
from eth_utils import keccak

from app.indexer.provider import ChainLog, EthereumLogProvider
from app.indexer.rpc import EthereumJsonRpcClient, RawEthereumLog, RpcResponseError


class LogDecoder(Protocol):
    def decode(self, chain_id: int, raw_log: RawEthereumLog) -> ChainLog | None: ...


class JsonAbiEventDecoder:
    """Decode any events present in one exact ABI, including tuple event fields.

    This generic decoder does not decide which decoded events are authoritative
    projections. A version-specific indexer must still validate its ABI and map
    only the expected events into database state.
    """

    def __init__(self, abi_path: str | Path, *, event_names: set[str] | None = None) -> None:
        path = Path(abi_path)
        if not path.is_file():
            raise ValueError(f"ABI file does not exist: {path}")
        document = json.loads(path.read_text(encoding="utf-8"))
        abi = document.get("abi") if isinstance(document, dict) else document
        if not isinstance(abi, list):
            raise ValueError("ABI must be a JSON list or an object containing an abi list")

        self.events_by_name: dict[str, dict[str, object]] = {}
        self.events_by_topic: dict[str, dict[str, object]] = {}
        for entry in abi:
            if not isinstance(entry, dict) or entry.get("type") != "event":
                continue
            name = entry.get("name")
            inputs = entry.get("inputs")
            if not isinstance(name, str) or not isinstance(inputs, list):
                raise ValueError("ABI contains a malformed event")
            if event_names is not None and name not in event_names:
                continue
            if not all(isinstance(field, dict) for field in inputs):
                raise ValueError(f"ABI event {name} contains malformed inputs")
            signature = f"{name}({','.join(self._canonical_type(field) for field in inputs)})"
            topic = "0x" + keccak(text=signature).hex()
            if topic in self.events_by_topic:
                raise ValueError(f"ABI contains duplicate event signature {signature}")
            self.events_by_name[name] = entry
            self.events_by_topic[topic] = entry

    def decode(self, chain_id: int, raw_log: RawEthereumLog) -> ChainLog | None:
        event, values = self.decode_values(raw_log)
        if event is None or values is None:
            return None
        payload = {
            self._snake_case(str(field["name"])): self._json_value(field, values[str(field["name"])])
            for field in event["inputs"]
        }
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

    def decode_values(
        self, raw_log: RawEthereumLog
    ) -> tuple[dict[str, object] | None, dict[str, object] | None]:
        if not raw_log.topics:
            raise RpcResponseError("event log has no signature topic")
        event = self.events_by_topic.get(raw_log.topics[0].lower())
        if event is None:
            return None, None

        inputs = event["inputs"]
        indexed = [field for field in inputs if field["indexed"]]
        plain = [field for field in inputs if not field["indexed"]]
        if len(raw_log.topics) != len(indexed) + 1:
            raise RpcResponseError("event topic count does not match ABI")
        values: dict[str, object] = {}
        try:
            for field, topic in zip(indexed, raw_log.topics[1:], strict=True):
                if self._indexed_value_is_hash(field):
                    values[str(field["name"])] = topic.lower()
                else:
                    values[str(field["name"])] = decode(
                        [self._canonical_type(field)], bytes.fromhex(topic[2:])
                    )[0]
            decoded_plain = decode(
                [self._canonical_type(field) for field in plain], bytes.fromhex(raw_log.data[2:])
            )
        except (DecodingError, ValueError, TypeError) as exc:
            raise RpcResponseError(f"could not decode {event['name']} event") from exc
        for field, value in zip(plain, decoded_plain, strict=True):
            values[str(field["name"])] = value
        return event, values

    @classmethod
    def _canonical_type(cls, field: dict[str, object]) -> str:
        abi_type = field.get("type")
        if not isinstance(abi_type, str):
            raise ValueError("ABI event field is missing its type")
        if not abi_type.startswith("tuple"):
            return abi_type
        components = field.get("components")
        if not isinstance(components, list) or not all(isinstance(item, dict) for item in components):
            raise ValueError("ABI tuple field is missing components")
        suffix = abi_type[len("tuple"):]
        return f"({','.join(cls._canonical_type(component) for component in components)}){suffix}"

    @staticmethod
    def _indexed_value_is_hash(field: dict[str, object]) -> bool:
        abi_type = str(field.get("type", ""))
        return abi_type in {"string", "bytes"} or abi_type.startswith("tuple") or "[" in abi_type

    @classmethod
    def _json_value(cls, field: dict[str, object], value: object) -> object:
        components = field.get("components")
        abi_type = str(field.get("type", ""))
        tuple_array = abi_type.startswith("tuple") and "[" in abi_type
        if isinstance(value, (tuple, list)):
            if isinstance(components, list) and not tuple_array:
                return {
                    cls._snake_case(str(component.get("name", f"field_{index}"))): cls._json_value(
                        component, item
                    )
                    for index, (component, item) in enumerate(zip(components, value, strict=True))
                    if isinstance(component, dict)
                }
            if tuple_array and isinstance(components, list):
                tuple_field = {"type": "tuple", "components": components}
                return [cls._json_value(tuple_field, item) for item in value]
            return [cls._json_value({}, item) for item in value]
        if isinstance(value, bytes):
            return "0x" + value.hex()
        if isinstance(value, str) and value.startswith("0x") and len(value) == 42:
            return value.lower()
        return value

    @staticmethod
    def _snake_case(value: str) -> str:
        # Preserve acronym groups as a unit: ``evidenceURI`` becomes
        # ``evidence_uri`` rather than ``evidence_u_r_i``.
        value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower()


class JsonAbiLogDecoder:
    """Strict M3 decoder; ignores ABI events outside the approved M3 surface."""

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
        self.decoder = JsonAbiEventDecoder(abi_path, event_names=set(self.REQUIRED_EVENTS))
        for event_name, expected in self.REQUIRED_EVENTS.items():
            event = self.decoder.events_by_name.get(event_name)
            if not isinstance(event, dict) or not self._matches(event, expected):
                raise ValueError(f"ABI event {event_name} does not match the approved interface")

    def decode(self, chain_id: int, raw_log: RawEthereumLog) -> ChainLog | None:
        event, values = self.decoder.decode_values(raw_log)
        if event is None or values is None:
            return None
        event_name = str(event["name"])
        if event_name == "MarketCreated":
            payload = {
                "market_id": values["marketId"],
                "creator": values["creator"],
                "question": values["question"],
                "trading_deadline": values["tradingDeadline"],
            }
        else:
            payload = {
                "market_id": values["marketId"],
                "trader": values["trader"],
                "outcome": values["outcome"],
                "shares": values["shares"],
                "cost": values["cost"],
                "yes_quantity": values["yesQuantity"],
                "no_quantity": values["noQuantity"],
            }
        return ChainLog(
            chain_id=chain_id,
            contract_address=raw_log.address,
            block_number=raw_log.block_number,
            block_hash=raw_log.block_hash,
            transaction_hash=raw_log.transaction_hash,
            log_index=raw_log.log_index,
            event_name=event_name,
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
