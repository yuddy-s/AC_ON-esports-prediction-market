"""Least-privilege PredictionMarket gateways for the registrar and proposer workers."""

from datetime import datetime

from eth_abi import decode, encode
from eth_account import Account
from eth_utils import keccak, to_checksum_address
from sqlalchemy import select

from app.database import SessionLocal
from app.indexer.rpc import EthereumJsonRpcClient, RpcError, RpcResponseError, RpcTransientError
from app.models import Fixture, IndexedMarket, OracleProposalIntent
from app.oracle_worker import (
    ClosedMarketRef, OracleGatewayUnavailable, OracleSubmissionUncertain, ProposalState,
)
from app.registration_worker import GatewayUnavailable, RegistrationState, SubmissionUncertain


FIXTURE_DATA_TYPE = "(string,string,string,string,string,string,string,uint256,bytes32,string)"
FIXTURE_TYPE = f"({FIXTURE_DATA_TYPE},address,bytes32,bool,bool,uint256)"
MARKET_TYPE = "(uint256,bytes32,string,uint256,uint8,address,uint256,uint256,uint256)"
RESOLUTION_TYPE = "(bool,uint8,address,bytes32,string,uint256,address,bytes32,uint256,uint8,bool,uint8)"
FIXTURE_NOT_REGISTERED = "0x" + keccak(text="FixtureNotRegistered(bytes32)")[:4].hex()


def _calldata(signature: str, types: list[str], values: list[object]) -> str:
    return "0x" + (keccak(text=signature)[:4] + encode(types, values)).hex()


def fixture_key(snapshot: dict[str, object]) -> bytes:
    return keccak(encode(
        ["string", "string", "string"],
        [str(snapshot["provider_id"]), str(snapshot["game_id"]), str(snapshot["external_match_id"])],
    ))


def _fixture_tuple(snapshot: dict[str, object]) -> tuple[object, ...]:
    scheduled = int(datetime.fromisoformat(str(snapshot["scheduled_start"]).replace("Z", "+00:00")).timestamp())
    evidence_hash = bytes.fromhex(str(snapshot["evidence_hash"])[2:])
    return (
        str(snapshot["provider_id"]), str(snapshot["game_id"]), str(snapshot["external_match_id"]),
        str(snapshot["team_a_id"]), str(snapshot["team_b_id"]), str(snapshot["team_a_name"]),
        str(snapshot["team_b_name"]), scheduled, evidence_hash, str(snapshot["evidence_url"]),
    )


class _SignedContractGateway:
    def __init__(
        self, rpc: EthereumJsonRpcClient, contract_address: str, private_key: str,
        chain_id: int, confirmation_depth: int = 2,
    ) -> None:
        self.rpc = rpc
        # eth-account rejects a mixed/lowercase transaction target unless it
        # is a valid EIP-55 checksum address.
        self.contract_address = to_checksum_address(contract_address)
        self.account = Account.from_key(private_key)
        self.chain_id = chain_id
        self.confirmation_depth = confirmation_depth
        if rpc.chain_id() != chain_id:
            raise ValueError("signer RPC chain ID does not match configuration")

    def _send(self, data: str, uncertain_error: type[RuntimeError]) -> str:
        try:
            nonce = self.rpc.transaction_count(self.account.address)
            estimate_request = {
                "from": self.account.address, "to": self.contract_address,
                "data": data, "value": "0x0",
            }
            gas = self.rpc.estimate_gas(estimate_request)
            transaction = {
                "chainId": self.chain_id,
                "nonce": nonce,
                "to": self.contract_address,
                "data": data,
                "value": 0,
                "gas": (gas * 120 + 99) // 100,
                "gasPrice": self.rpc.gas_price(),
            }
            signed = self.account.sign_transaction(transaction)
        except RpcError as exc:
            raise GatewayUnavailable(str(exc)) from exc
        try:
            return self.rpc.send_raw_transaction(signed.raw_transaction)
        except RpcTransientError as exc:
            raise uncertain_error(str(exc)) from exc
        except RpcError as exc:
            raise GatewayUnavailable(str(exc)) from exc

    def _receipt_state(self, transaction_hash: str) -> str:
        try:
            receipt = self.rpc.transaction_receipt(transaction_hash)
            if receipt is None:
                return "pending"
            status = int(str(receipt.get("status", "0x0")), 16)
            if status != 1:
                return "reverted"
            block_number = int(str(receipt["blockNumber"]), 16)
            confirmations = self.rpc.latest_block() - block_number + 1
            return "success" if confirmations >= self.confirmation_depth else "pending"
        except RpcTransientError as exc:
            raise GatewayUnavailable(str(exc)) from exc
        except (RpcError, KeyError, TypeError, ValueError):
            return "unknown"


class PredictionMarketRegistrationGateway(_SignedContractGateway):
    def registration_state(self, snapshot: dict[str, object]) -> RegistrationState:
        key = fixture_key(snapshot)
        data = _calldata("getFixture(bytes32)", ["bytes32"], [key])
        try:
            raw = self.rpc.eth_call(self.contract_address, data)
            decoded = decode([FIXTURE_TYPE], bytes.fromhex(raw[2:]))[0]
        except RpcTransientError as exc:
            raise GatewayUnavailable(str(exc)) from exc
        except RpcResponseError as exc:
            if FIXTURE_NOT_REGISTERED in str(exc).lower():
                return "absent"
            raise GatewayUnavailable(str(exc)) from exc
        except (ValueError, TypeError) as exc:
            raise GatewayUnavailable("invalid getFixture response") from exc
        if not decoded[3]:
            return "absent"
        return "matching" if tuple(decoded[0]) == _fixture_tuple(snapshot) else "conflicting"

    def receipt_state(self, transaction_hash: str) -> str:
        return self._receipt_state(transaction_hash)

    def submit(self, snapshot: dict[str, object]) -> str:
        data = _calldata(
            f"registerFixture({FIXTURE_DATA_TYPE})", [FIXTURE_DATA_TYPE], [_fixture_tuple(snapshot)]
        )
        return self._send(data, SubmissionUncertain)


class PredictionMarketOracleGateway(_SignedContractGateway):
    def closed_markets(self) -> list[ClosedMarketRef]:
        refs: list[ClosedMarketRef] = []
        with SessionLocal() as session:
            markets = session.scalars(select(IndexedMarket).where(
                IndexedMarket.chain_id == self.chain_id,
                IndexedMarket.contract_address == self.contract_address,
                IndexedMarket.state == "CLOSED",
                IndexedMarket.fixture_key.is_not(None),
            )).all()
            fixtures = session.scalars(select(Fixture)).all()
            by_key = {
                "0x" + fixture_key({
                    "provider_id": fixture.provider_id,
                    "game_id": fixture.game_id,
                    "external_match_id": fixture.external_match_id,
                }).hex(): fixture.id
                for fixture in fixtures
            }
            for market in markets:
                fixture_id = by_key.get(str(market.fixture_key).lower())
                if fixture_id is not None:
                    refs.append(ClosedMarketRef(self.chain_id, self.contract_address, market.market_id, fixture_id))
        return refs

    def proposal_state(
        self, market: ClosedMarketRef, intent: OracleProposalIntent | None
    ) -> ProposalState:
        try:
            market_raw = self.rpc.eth_call(
                self.contract_address,
                _calldata("getMarket(uint256)", ["uint256"], [market.market_id]),
            )
            market_data = decode([MARKET_TYPE], bytes.fromhex(market_raw[2:]))[0]
            resolution_raw = self.rpc.eth_call(
                self.contract_address,
                _calldata("getResolution(uint256)", ["uint256"], [market.market_id]),
            )
            resolution = decode([RESOLUTION_TYPE], bytes.fromhex(resolution_raw[2:]))[0]
        except (RpcError, ValueError, TypeError) as exc:
            raise OracleGatewayUnavailable(str(exc)) from exc
        if bool(resolution[0]):
            if intent is None:
                return "proposed_conflicting"
            expected = {"YES": 0, "NO": 1, "VOID": 2}[intent.outcome]
            matches = (
                int(resolution[1]) == expected
                and "0x" + bytes(resolution[3]).hex() == intent.evidence_hash.lower()
                and str(resolution[4]) == intent.evidence_url
            )
            return "proposed_matching" if matches else "proposed_conflicting"
        return "closed_unproposed" if int(market_data[4]) == 1 else "not_closed"

    def receipt_state(self, transaction_hash: str) -> str:
        try:
            return self._receipt_state(transaction_hash)
        except GatewayUnavailable as exc:
            raise OracleGatewayUnavailable(str(exc)) from exc

    def submit(self, intent: OracleProposalIntent) -> str:
        outcome = {"YES": 0, "NO": 1, "VOID": 2}[intent.outcome]
        data = _calldata(
            "proposeOutcome(uint256,uint8,bytes32,string)",
            ["uint256", "uint8", "bytes32", "string"],
            [intent.market_id, outcome, bytes.fromhex(intent.evidence_hash[2:]), intent.evidence_url],
        )
        try:
            return self._send(data, OracleSubmissionUncertain)
        except GatewayUnavailable as exc:
            raise OracleGatewayUnavailable(str(exc)) from exc
