"""Validate the public, versioned Sepolia deployment handoff."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from eth_utils import is_checksum_address

from app.indexer.decoder import JsonAbiLogDecoder


HEX_40 = re.compile(r"^[0-9a-f]{40}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
TX_HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")
ABI_FILENAME = re.compile(
    r"^(ACONTestToken|PredictionMarket)\.([0-9a-f]{12})\.([0-9a-f]{12})\.abi\.json$"
)
REQUIRED_FUNCTIONS = {
    "ACONTestToken": {
        "faucet": ((), ("uint256",)),
        "approve": (("address", "uint256"), ("bool",)),
        "balanceOf": (("address",), ("uint256",)),
        "allowance": (("address", "address"), ("uint256",)),
        "hasClaimedFaucet": (("address",), ("bool",)),
        "decimals": ((), ("uint8",)),
    },
    "PredictionMarket": {
        "paymentToken": ((), ("address",)),
        "marketCount": ((), ("uint256",)),
        "createMarket": (("string", "uint256"), ("uint256",)),
        "getMarket": (("uint256",), ("string", "uint256", "uint8", "address", "uint256", "uint256")),
        "quoteBuy": (("uint256", "uint8", "uint256"), ("uint256",)),
        "buy": (("uint256", "uint8", "uint256", "uint256"), ("uint256",)),
        "balanceOf": (("uint256", "address", "uint8"), ("uint256",)),
    },
}


@dataclass(frozen=True, slots=True)
class ContractDeployment:
    address: str
    deployment_transaction_hash: str
    deployment_block: int
    abi_path: Path
    abi_sha256: str

    @property
    def abi_version(self) -> str:
        return self.abi_path.name


@dataclass(frozen=True, slots=True)
class ExampleTransaction:
    transaction_hash: str
    block_number: int


@dataclass(frozen=True, slots=True)
class DeploymentHandoff:
    source_commit: str
    chain_id: int
    confirmation_depth: int
    token: ContractDeployment
    market: ContractDeployment
    demo_market_id: int
    creation: ExampleTransaction
    trade: ExampleTransaction


def _fields(value: object, expected: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} must have exactly: {', '.join(sorted(expected))}")
    return value


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _transaction(value: object, label: str) -> ExampleTransaction:
    fields = _fields(value, {"transaction_hash", "block_number"}, label)
    transaction_hash = fields["transaction_hash"]
    if not isinstance(transaction_hash, str) or not TX_HASH.fullmatch(transaction_hash):
        raise ValueError(f"{label}.transaction_hash must be a 32-byte hex hash")
    return ExampleTransaction(
        transaction_hash=transaction_hash.lower(),
        block_number=_nonnegative_integer(fields["block_number"], f"{label}.block_number"),
    )


def _contract(
    value: object, label: str, source_commit: str, repo_root: Path
) -> ContractDeployment:
    fields = _fields(
        value,
        {"address", "deployment_transaction_hash", "deployment_block", "abi_path", "abi_sha256"},
        label,
    )
    address = fields["address"]
    if not isinstance(address, str) or not is_checksum_address(address):
        raise ValueError(f"{label}.address must be a checksummed Ethereum address")
    deployment = _transaction(
        {"transaction_hash": fields["deployment_transaction_hash"], "block_number": fields["deployment_block"]},
        f"{label}.deployment",
    )
    abi_sha256 = fields["abi_sha256"]
    if not isinstance(abi_sha256, str) or not HEX_64.fullmatch(abi_sha256):
        raise ValueError(f"{label}.abi_sha256 must be a lowercase SHA-256 digest")
    abi_path_value = fields["abi_path"]
    if not isinstance(abi_path_value, str):
        raise ValueError(f"{label}.abi_path must be a repository-relative path")
    relative_path = Path(abi_path_value)
    expected_prefix = Path("deployments") / "abi"
    if relative_path.parent != expected_prefix:
        raise ValueError(f"{label}.abi_path must be under deployments/abi")
    match = ABI_FILENAME.fullmatch(relative_path.name)
    if not match or match.group(1) != label:
        raise ValueError(f"{label}.abi_path has an invalid versioned filename")
    if match.group(2) != source_commit[:12] or match.group(3) != abi_sha256[:12]:
        raise ValueError(f"{label}.abi_path version does not match source commit and ABI digest")
    abi_path = (repo_root / relative_path).resolve()
    if not abi_path.is_relative_to(repo_root.resolve()) or not abi_path.is_file():
        raise ValueError(f"{label}.abi_path does not identify a checked-in ABI file")
    if hashlib.sha256(abi_path.read_bytes()).hexdigest() != abi_sha256:
        raise ValueError(f"{label}.abi_sha256 does not match the ABI file")
    try:
        abi_document = json.loads(abi_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label}.abi_path is not valid JSON") from exc
    abi = abi_document.get("abi") if isinstance(abi_document, dict) else abi_document
    if not isinstance(abi, list):
        raise ValueError(f"{label}.abi_path must contain an ABI list")
    _required_functions(abi, label)
    if label == "PredictionMarket":
        JsonAbiLogDecoder(abi_path)
    return ContractDeployment(address, deployment.transaction_hash, deployment.block_number, abi_path, abi_sha256)


def _required_functions(abi: list[object], label: str) -> None:
    functions = {
        entry.get("name"): entry
        for entry in abi
        if isinstance(entry, dict) and entry.get("type") == "function"
    }
    for name, (inputs, outputs) in REQUIRED_FUNCTIONS[label].items():
        entry = functions.get(name)
        if not isinstance(entry, dict):
            raise ValueError(f"{label} ABI is missing function {name}")
        actual_inputs = entry.get("inputs")
        actual_outputs = entry.get("outputs")
        if not isinstance(actual_inputs, list) or not isinstance(actual_outputs, list):
            raise ValueError(f"{label} ABI function {name} has malformed inputs or outputs")
        if not all(isinstance(field, dict) for field in [*actual_inputs, *actual_outputs]):
            raise ValueError(f"{label} ABI function {name} has malformed inputs or outputs")
        input_types = tuple(field.get("type") for field in actual_inputs)
        output_types = tuple(field.get("type") for field in actual_outputs)
        if input_types != inputs or output_types != outputs:
            raise ValueError(f"{label} ABI function {name} does not match the M3 interface")


def load_deployment_handoff(path: str | Path, *, repo_root: Path | None = None) -> DeploymentHandoff:
    """Load a completed public handoff, rejecting placeholders, secrets, and ABI drift."""
    root = repo_root or Path(__file__).resolve().parents[3]
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("deployment manifest is missing or invalid JSON") from exc
    fields = _fields(
        document,
        {"manifest_version", "network", "chain_id", "source_commit", "confirmation_depth", "token", "market", "demo"},
        "manifest",
    )
    if (
        type(fields["manifest_version"]) is not int
        or fields["manifest_version"] != 1
        or fields["network"] != "ethereum-sepolia"
    ):
        raise ValueError("unsupported deployment manifest version or network")
    if fields["chain_id"] != 11155111:
        raise ValueError("deployment manifest must target Ethereum Sepolia (11155111)")
    source_commit = fields["source_commit"]
    if not isinstance(source_commit, str) or not HEX_40.fullmatch(source_commit):
        raise ValueError("source_commit must be a full lowercase Git commit SHA")
    confirmation_depth = _nonnegative_integer(fields["confirmation_depth"], "confirmation_depth")
    token = _contract(fields["token"], "ACONTestToken", source_commit, root)
    market = _contract(fields["market"], "PredictionMarket", source_commit, root)
    demo = _fields(fields["demo"], {"market_id", "creation", "trade"}, "demo")
    creation = _transaction(demo["creation"], "demo.creation")
    trade = _transaction(demo["trade"], "demo.trade")
    if not token.deployment_block <= market.deployment_block <= creation.block_number <= trade.block_number:
        raise ValueError("deployment and demo blocks must be in chain order")
    return DeploymentHandoff(
        source_commit=source_commit,
        chain_id=11155111,
        confirmation_depth=confirmation_depth,
        token=token,
        market=market,
        demo_market_id=_nonnegative_integer(demo["market_id"], "demo.market_id"),
        creation=creation,
        trade=trade,
    )
