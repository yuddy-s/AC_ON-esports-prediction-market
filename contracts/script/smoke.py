"""Contract journeys on a fresh local Anvil node; no private keys required.

Run from contracts/: python3 script/smoke.py --rpc-url http://127.0.0.1:18545
Only localhost chain 31337 is accepted. Uses unlocked/impersonated Anvil accounts,
real ACON/pricing/market/registry contracts, and the explicit test VRF mock.
This is not a hosted frontend/backend test or proof of live Chainlink fulfillment.
"""

import argparse
import json
from pathlib import Path
import shutil
import socket
import subprocess
import time
import urllib.request
from urllib.parse import urlparse


class Harness:
    def __init__(self, url):
        if urlparse(url).hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Only a local Anvil URL is allowed")
        self.url = url
        self.foundry = Path.home() / ".foundry/bin"
        self.receipts = []
        self.logs = []
        if int(self.rpc("eth_chainId", []), 16) != 31337:
            raise ValueError("Expected Anvil chain 31337")
        self.accounts = self.rpc("eth_accounts", [])
        self.admin, self.registrar, self.proposer, self.challenger, self.trader = self.accounts[:5]
        if int(self.rpc("eth_getTransactionCount", [self.admin, "latest"]), 16) != 0:
            raise ValueError("Start a fresh Anvil node; the administrator nonce must be zero")

    def rpc(self, method, params):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        request = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        if "error" in result:
            raise RuntimeError(f"{method}: {result['error']}")
        return result["result"]

    def tool(self, name, *args):
        executable = shutil.which(name) or str(self.foundry / name)
        result = subprocess.run([executable, *map(str, args)], capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        return result.stdout.strip()

    def calldata(self, signature, *args):
        return self.tool("cast", "calldata", signature, *args)

    def call(self, target, signature, *args):
        return self.rpc("eth_call", [{"to": target, "data": self.calldata(signature, *args)}, "latest"])

    def number(self, target, signature, *args):
        return int(self.call(target, signature, *args), 16)

    def decode(self, signature, encoded):
        result = json.loads(self.tool("cast", "abi-decode", "--json", signature, encoded))
        if isinstance(result, dict) and "data" in result:
            assert result.get("success") is True, result
            return result["data"]
        return result

    def transaction(self, sender, target, data, label):
        transaction = {"from": sender, "data": data, "value": "0x0"}
        if target:
            transaction["to"] = target
        estimate = int(self.rpc("eth_estimateGas", [transaction]), 16)
        transaction["gas"] = hex((estimate * 120 + 99) // 100)
        tx_hash = self.rpc("eth_sendTransaction", [transaction])
        for _ in range(100):
            receipt = self.rpc("eth_getTransactionReceipt", [tx_hash])
            if receipt:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("Receipt timeout; inspect chain before retrying")
        assert int(receipt["status"], 16) == 1, (label, receipt)
        self.receipts.append({"action": label, "hash": tx_hash, "block": int(receipt["blockNumber"], 16), "gas_used": int(receipt["gasUsed"], 16)})
        self.logs.extend(receipt["logs"])
        return receipt

    def send(self, sender, target, signature, *args):
        return self.transaction(sender, target, self.calldata(signature, *args), signature.split("(")[0])

    def deploy(self, name, constructor_signature=None, *args):
        bytecode = self.tool("forge", "inspect", name, "bytecode")
        assert bytecode.startswith("0x") and "__" not in bytecode
        if constructor_signature:
            bytecode += self.tool("cast", "abi-encode", constructor_signature, *args)[2:]
        receipt = self.transaction(self.admin, None, bytecode, "deploy " + name)
        return receipt["contractAddress"]

    def advance(self, seconds):
        self.rpc("evm_increaseTime", [seconds])
        self.rpc("evm_mine", [])

    def now(self):
        return int(self.rpc("eth_getBlockByNumber", ["latest", False])["timestamp"], 16)

    def market_data(self, market, market_id):
        return self.decode("f()((uint256,bytes32,string,uint256,uint8,address,uint256,uint256,uint256))", self.call(market, "getMarket(uint256)", market_id))[0]

    def round_data(self, market, market_id, round_id):
        return self.decode("f()((uint256,uint256,uint256,uint256,bool,bool,bool,address[],address[5],uint8[3]))", self.call(market, "getResolverRound(uint256,uint8)", market_id, round_id))[0]


def run(url, output):
    h = Harness(url)
    token = h.deploy("ACONTestToken")
    pricing = h.deploy("MarketPricing")
    registry = h.deploy("ResolverRegistry", "f(address)", h.admin)
    coordinator = h.deploy("VRFCoordinatorMock")
    config = f"({token},{pricing},{registry},{coordinator},{h.admin},0x{'0'*63}1,1,2000000)"
    market = h.deploy("PredictionMarket", "f((address,address,address,address,address,bytes32,uint256,uint32))", config)
    roles = {name: h.call(market, name + "()") for name in ("REGISTRAR_ROLE", "PROPOSER_ROLE")}
    h.send(h.admin, market, "grantRole(bytes32,address)", roles["REGISTRAR_ROLE"], h.registrar)
    h.send(h.admin, market, "grantRole(bytes32,address)", roles["PROPOSER_ROLE"], h.proposer)
    resolvers = ["0x" + format(0x1000 + i, "040x") for i in range(10)]
    for resolver in resolvers:
        h.rpc("anvil_impersonateAccount", [resolver])
        h.rpc("anvil_setBalance", [resolver, hex(100 * 10**18)])
        h.send(h.admin, registry, "setResolverStatus(address,bool)", resolver, "true")
    for wallet in (h.admin, h.challenger, h.trader):
        h.send(wallet, token, "faucet()")
        h.send(wallet, token, "approve(address,uint256)", market, 1000 * 10**18)
    evidence = h.tool("cast", "keccak", "explicit fictional Anvil fixture")
    fixture_tuple = "(string,string,string,string,string,string,string,uint256,bytes32,string)"

    def create(index):
        now = h.now()
        data = f'(manual,valorant,anvil-{index},team-a,team-b,"Team A","Team B",{now+15*86400},{evidence},https://example.invalid/anvil)'
        h.send(h.registrar, market, "registerFixture(" + fixture_tuple + ")", data)
        key = h.call(market, "computeFixtureKey(string,string,string)", "manual", "valorant", "anvil-" + str(index))
        revision = h.tool("cast", "keccak", h.tool("cast", "abi-encode", "f(" + fixture_tuple + ")", data))
        market_id = h.number(market, "marketCount()")
        h.send(h.admin, market, "createMarket(bytes32,uint256,bytes32)", key, now + 2 * 86400, revision)
        return market_id

    def buy(market_id, side, shares):
        cost = h.number(market, "quoteBuy(uint256,uint8,uint256)", market_id, side, shares)
        before = h.number(token, "balanceOf(address)", h.trader)
        h.send(h.trader, market, "buy(uint256,uint8,uint256,uint256)", market_id, side, shares, cost)
        assert h.number(token, "balanceOf(address)", h.trader) == before - cost

    def close(market_id):
        h.send(h.registrar, market, "closeTrading(uint256,bytes32)", market_id, evidence)

    def propose(market_id, choice):
        h.send(h.proposer, market, "proposeOutcome(uint256,uint8,bytes32,string)", market_id, choice, evidence, "https://example.invalid/result")

    def challenge(market_id):
        h.send(h.challenger, market, "challengeOutcome(uint256,bytes32)", market_id, evidence)
        return h.send(h.admin, market, "requestResolverSelection(uint256)", market_id)

    def fulfill(market_id, round_id):
        info = h.round_data(market, market_id, round_id)
        h.send(h.admin, coordinator, "fulfill(address,uint256,uint256)", market, int(info[3]), 123 + round_id)
        return h.round_data(market, market_id, round_id)[8]

    def vote_quorum(market_id, committee, choice):
        for resolver in committee[:3]:
            h.send(resolver, market, "voteOnOutcome(uint256,uint8)", market_id, choice)

    def claim(market_id, expected, final_state=6):
        assert int(h.market_data(market, market_id)[4]) == final_state
        assert h.number(market, "claimableAmount(uint256,address)", market_id, h.trader) == expected
        before = h.number(token, "balanceOf(address)", h.trader)
        h.send(h.trader, market, "claimPayout(uint256)", market_id)
        assert h.number(token, "balanceOf(address)", h.trader) == before + expected
        assert h.number(market, "hasClaimed(uint256,address)", market_id, h.trader) == 1
        h.send(h.admin, market, "withdrawCreatorSurplus(uint256)", market_id)

    results = []
    normal = create(0)
    buy(normal, 0, 10 * 10**18); buy(normal, 1, 4 * 10**18)
    proceeds = h.number(market, "quoteSell(uint256,uint8,uint256)", normal, 0, 2 * 10**18)
    before = h.number(token, "balanceOf(address)", h.trader)
    h.send(h.trader, market, "sell(uint256,uint8,uint256,uint256)", normal, 0, 2 * 10**18, proceeds)
    assert h.number(token, "balanceOf(address)", h.trader) == before + proceeds
    close(normal); propose(normal, 0); h.advance(86400)
    h.send(h.admin, market, "finalize(uint256)", normal); claim(normal, 8 * 10**18)
    results.append("normal proposal, guarded buy/sell, winning claim, creator surplus")

    disputed = create(1); buy(disputed, 0, 10 * 10**18); close(disputed); propose(disputed, 1)
    bond_before = h.number(token, "balanceOf(address)", h.challenger)
    h.send(h.admin, coordinator, "setFailure(bool)", "true")
    failed_receipt = challenge(disputed)
    failed_round = h.round_data(market, disputed, 1)
    assert int(h.market_data(market, disputed)[4]) == 4
    assert failed_round[4] is True and failed_round[5] is False and failed_round[6] is False
    assert len(failed_round[7]) == len(resolvers)

    # The coordinator reverts, but the successful outer transaction captures the market's failure event.
    failure_topic = h.tool("cast", "keccak", "ResolverSelectionRequestFailed(uint256,uint8,bytes32,uint256)")
    failure_logs = [log for log in failed_receipt["logs"]
                    if log["address"].lower() == market.lower() and log["topics"][0] == failure_topic]
    assert len(failure_logs) == 1, "Missing captured VRF request-failure event"
    failure_log = failure_logs[0]
    assert len(failure_log["topics"]) == 3
    assert int(failure_log["topics"][1], 16) == disputed and int(failure_log["topics"][2], 16) == 1
    reason_hash, retry_after = h.decode("f()(bytes32,uint256)", failure_log["data"])
    assert reason_hash == h.tool("cast", "keccak", h.calldata("RequestFailed()"))
    failed_block = h.rpc("eth_getBlockByHash", [failed_receipt["blockHash"], False])
    failed_at = int(failed_block["timestamp"], 16)
    assert int(failed_round[2]) == failed_at
    assert int(retry_after) == failed_at + 30 * 60
    assert int(failed_round[0]) == failed_at + 7 * 86400

    h.send(h.admin, coordinator, "setFailure(bool)", "false")
    h.advance(30 * 60)
    h.send(h.admin, market, "retryResolverSelection(uint256)", disputed)
    original_round = h.round_data(market, disputed, 1)
    assert original_round[4] is True and original_round[5] is True
    assert original_round[0] == failed_round[0] and original_round[7] == failed_round[7]
    h.advance(30 * 60)
    h.send(h.admin, market, "retryResolverSelection(uint256)", disputed)
    retried_round = h.round_data(market, disputed, 1)
    assert retried_round[0] == failed_round[0] and retried_round[7] == failed_round[7]
    assert retried_round[5] is True and retried_round[3] != original_round[3]
    h.send(h.admin, coordinator, "fulfill(address,uint256,uint256)", market, int(original_round[3]), 999)
    assert int(h.market_data(market, disputed)[4]) == 4
    vote_quorum(disputed, fulfill(disputed, 1), 0)
    assert h.number(token, "balanceOf(address)", h.challenger) == bond_before
    claim(disputed, 10 * 10**18); results.append("disputed result, captured VRF request failure, recovery/retry/stale callback, committee, three votes, bond refund, claim")

    voided = create(2); buy(voided, 0, 6 * 10**18); buy(voided, 1, 4 * 10**18)
    close(voided); propose(voided, 2); h.advance(86400)
    h.send(h.admin, market, "finalize(uint256)", voided); claim(voided, 5 * 10**18, 7)
    results.append("unchallenged VOID, combined YES/NO claim")

    timeout = create(3); buy(timeout, 0, 4 * 10**18); close(timeout); h.advance(7 * 86400)
    h.send(h.admin, market, "requestResolverSelection(uint256)", timeout)
    vote_quorum(timeout, fulfill(timeout, 1), 0); claim(timeout, 4 * 10**18)
    results.append("seven-day no-proposal timeout, permissionless selection, claim")

    replacement = create(4); buy(replacement, 0, 6 * 10**18); close(replacement); propose(replacement, 0)
    challenge(replacement); fulfill(replacement, 1); h.advance(48 * 3600)
    h.send(h.admin, market, "advanceResolution(uint256)", replacement)
    fulfill(replacement, 2); h.advance(48 * 3600)
    h.send(h.admin, market, "advanceResolution(uint256)", replacement); claim(replacement, 3 * 10**18, 7)
    results.append("replacement committee, second-round no-quorum VOID, claim")

    shortage = create(5); buy(shortage, 0, 2 * 10**18); close(shortage); propose(shortage, 0)
    for resolver in resolvers: h.send(h.admin, registry, "setResolverStatus(address,bool)", resolver, "false")
    challenge(shortage); h.advance(7 * 86400)
    h.send(h.admin, market, "advanceResolution(uint256)", shortage); claim(shortage, 10**18, 7)
    results.append("insufficient resolver pool, fixed selection deadline, VOID, claim")
    assert h.number(market, "totalCollateral()") == 0 and h.number(market, "totalChallengeBonds()") == 0
    assert h.number(token, "balanceOf(address)", market) == 0
    h.rpc("evm_mine", []); h.rpc("evm_mine", [])
    head = int(h.rpc("eth_blockNumber", []), 16)
    assert all(receipt["block"] <= head - 2 for receipt in h.receipts)
    report = {"chain_id": 31337, "mode": "local Anvil / mock VRF / real ACON", "market": market,
              "pricing": pricing, "registry": registry, "token": token, "coordinator": coordinator,
              "journeys": results, "transactions": h.receipts, "logs": h.logs,
              "observed_head": head, "safe_checkpoint_at_depth_two": head - 2,
              "release_gates": ["team ABI freeze", "Matthew accounting sign-off", "real 2-of-3 Safe and funded Sepolia VRF", "fresh Sepolia deployment and transaction smoke"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    for result in results: print("PASS:", result)
    print("PASS: all per-market payouts/surplus completed; token balance, collateral, and bond escrow reconcile to zero")
    print("Evidence:", output)


def run_with_anvil(url, output):
    """Own one disposable node and always stop it, including on a failed journey."""
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port or parsed.path:
        raise ValueError("--start-anvil requires http://127.0.0.1:<unused-port>")
    with socket.socket() as probe:
        if probe.connect_ex((parsed.hostname, parsed.port)) == 0:
            raise ValueError("Port is already occupied; choose an unused port for the disposable node")
    output.parent.mkdir(parents=True, exist_ok=True)
    executable = shutil.which("anvil") or str(Path.home() / ".foundry/bin/anvil")
    with (output.parent / "anvil.log").open("w") as log:
        process = subprocess.Popen([executable, "--host", "127.0.0.1", "--port", str(parsed.port),
                                    "--timestamp", "1793404800"], stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Anvil exited before readiness; inspect anvil.log")
                try:
                    with socket.create_connection((parsed.hostname, parsed.port), timeout=0.1):
                        break
                except OSError:
                    time.sleep(0.05)
            else:
                raise RuntimeError("Anvil startup timed out")
            run(url, output)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc-url", default="http://127.0.0.1:18545")
    parser.add_argument("--output", type=Path, default=Path("cache/verification/anvil-smoke.json"))
    parser.add_argument("--start-anvil", action="store_true", help="Start and stop a fresh disposable local node")
    args = parser.parse_args()
    (run_with_anvil if args.start_anvil else run)(args.rpc_url, args.output)
