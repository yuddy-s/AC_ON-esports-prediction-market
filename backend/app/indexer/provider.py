from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True, slots=True)
class ChainLog:
    chain_id: int
    contract_address: str
    block_number: int
    block_hash: str
    transaction_hash: str
    log_index: int
    event_name: str
    payload: dict[str, object]


class EthereumLogProvider(Protocol):
    """Provider boundary; ABI decoding will be added after the trade ABI freezes."""

    def latest_block(self) -> int: ...

    def block_hash(self, block_number: int) -> str: ...

    def get_logs(self, contract_address: str, from_block: int, to_block: int) -> Sequence[ChainLog]: ...
