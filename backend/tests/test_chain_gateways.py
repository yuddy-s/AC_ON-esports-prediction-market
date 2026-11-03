from datetime import UTC, datetime

from eth_abi import encode
from eth_account import Account

from app.chain_gateways import (
    FIXTURE_TYPE, MARKET_TYPE, RESOLUTION_TYPE, PredictionMarketOracleGateway,
    PredictionMarketRegistrationGateway, _fixture_tuple,
)
from app.models import OracleProposalIntent
from app.oracle_worker import ClosedMarketRef


CONTRACT = "0x" + "11" * 20
KEY = "0x" + "22" * 32
TX = "0x" + "33" * 32


def snapshot() -> dict[str, object]:
    return {
        "provider_id": "pandascore", "game_id": "valorant", "external_match_id": "42",
        "scheduled_start": datetime(2030, 1, 2, tzinfo=UTC).isoformat(),
        "team_a_id": "a", "team_a_name": "Alpha", "team_b_id": "b", "team_b_name": "Bravo",
        "evidence_url": "https://organizer.example/match/42", "evidence_hash": "0x" + "44" * 32,
    }


class Rpc:
    def __init__(self) -> None:
        self.head = 11
        self.raw = b""
        self.call_results: list[str] = []

    def chain_id(self): return 31337
    def transaction_count(self, _address): return 0
    def estimate_gas(self, _tx): return 100_000
    def gas_price(self): return 1_000_000_000
    def send_raw_transaction(self, raw): self.raw = raw; return TX
    def latest_block(self): return self.head
    def transaction_receipt(self, _hash): return {"status": "0x1", "blockNumber": "0xb"}
    def eth_call(self, _address, _data): return self.call_results.pop(0)


def test_registration_gateway_encodes_submit_and_waits_for_confirmations() -> None:
    rpc = Rpc()
    data = _fixture_tuple(snapshot())
    rpc.call_results.append("0x" + encode(
        [FIXTURE_TYPE], [(data, Account.from_key(KEY).address, bytes.fromhex("55" * 32), True, False, 0)]
    ).hex())
    gateway = PredictionMarketRegistrationGateway(rpc, CONTRACT, KEY, 31337, confirmation_depth=2)

    assert gateway.registration_state(snapshot()) == "matching"
    assert gateway.submit(snapshot()) == TX
    assert rpc.raw
    assert gateway.receipt_state(TX) == "pending"
    rpc.head = 12
    assert gateway.receipt_state(TX) == "success"


def test_oracle_gateway_compares_the_reviewed_immutable_proposal() -> None:
    rpc = Rpc()
    market = (7, bytes.fromhex("66" * 32), "A beats B?", 1_900_000_000, 2, Account.from_key(KEY).address, 0, 0, 0)
    resolution = (True, 0, Account.from_key(KEY).address, bytes.fromhex("77" * 32), "https://organizer.example/result", 2_000_000_000, "0x" + "00" * 20, bytes(32), 0, 0, False, 0)
    rpc.call_results.extend([
        "0x" + encode([MARKET_TYPE], [market]).hex(),
        "0x" + encode([RESOLUTION_TYPE], [resolution]).hex(),
    ])
    gateway = PredictionMarketOracleGateway(rpc, CONTRACT, KEY, 31337)
    intent = OracleProposalIntent(
        chain_id=31337, contract_address=CONTRACT, market_id=7, fixture_id=1,
        observation_id=1, outcome="YES", evidence_url="https://organizer.example/result",
        evidence_hash="0x" + "77" * 32, status="submitted", attempts=1,
        created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
    )

    assert gateway.proposal_state(ClosedMarketRef(31337, CONTRACT, 7, 1), intent) == "proposed_matching"
    assert gateway.submit(intent) == TX
    assert rpc.raw
