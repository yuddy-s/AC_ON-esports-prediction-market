# Sepolia deployment — 2026-11-02

Status: **four contracts deployed and the 15-call Safe setup batch successfully executed**.
The Safe administers both contracts, the original registrar/proposer roles are granted, ten
resolvers are active, and the market is a consumer of the funded Safe-owned VRF subscription.
Real VRF fulfillment, lifecycle smoke, and whole-application acceptance remain pending.

## Release and addresses

- Network: Ethereum Sepolia, chain ID `11155111`.
- Source commit: `721a6fef039a479f46a76fd77fdc4f0f1937af7f`.
- Compiler: Solidity `0.8.24`, optimizer 200, via-IR, Cancun bytecode target.
- Indexer start block covering all four contracts: **12051217**.
- PredictionMarket deployment block: **12051223**.
- The [post-setup manifest](manifest.post-setup.json) contains current setup state, exact
  source-versioned ABI paths, full SHA-256 digests, and the Safe execution receipt.
  Its M4 schema still needs consumer review; it is not an M3 worker configuration file.
- The original [deployment manifest](manifest.json) and [verification snapshot](verification.json)
  preserve the pre-setup state. Use the post-setup manifest for integration.
- Start with the [integration handoff](INTEGRATION.md) for teammate responsibilities and public config.

| Contract | Live address | Deployment block |
|---|---|---:|
| ACONTestToken | [`0xf85b2278a810410c6AE0b7490d34671E0C8e6E90`](https://sepolia.etherscan.io/address/0xf85b2278a810410c6AE0b7490d34671E0C8e6E90) | 12051217 |
| MarketPricing | [`0x9d2bC542cD5028E360F16Bc8cE9043dBfCF1ceEA`](https://sepolia.etherscan.io/address/0x9d2bC542cD5028E360F16Bc8cE9043dBfCF1ceEA) | 12051219 |
| ResolverRegistry | [`0x72deD592bCDCFd92db58D1E99A83fDa36b54f831`](https://sepolia.etherscan.io/address/0x72deD592bCDCFd92db58D1E99A83fDa36b54f831) | 12051221 |
| PredictionMarket | [`0x03ae48f03C7822540a91DA2168602bd49dC510E9`](https://sepolia.etherscan.io/address/0x03ae48f03C7822540a91DA2168602bd49dC510E9) | 12051223 |

PredictionMarket ABI SHA-256:

```text
4af9297937eb1b1b277a8c8d83e78ceb05c5db66cb120f1d39b80fdfc1015a91
```

These are receipt-derived live addresses. Earlier dry-run predictions before the failed creation
consumed nonce 27 are obsolete.

## Confirmed transactions

All six successful transactions were individually confirmed and checked against the reviewed
creation bytecode, constructor arguments, or administration-transfer calldata.

| Step | Transaction |
|---|---|
| Deploy ACONTestToken | [`0xd0a77084b1a0464b505511a7909f1d94b09ca986c6bd3dbf4294c028b7b53ffb`](https://sepolia.etherscan.io/tx/0xd0a77084b1a0464b505511a7909f1d94b09ca986c6bd3dbf4294c028b7b53ffb) |
| Deploy MarketPricing | [`0x39beb78854fdc30ac2d228476f0c20879d73090df82c3b4d56cd4e7627347b78`](https://sepolia.etherscan.io/tx/0x39beb78854fdc30ac2d228476f0c20879d73090df82c3b4d56cd4e7627347b78) |
| Deploy ResolverRegistry | [`0xd8076df6138369617dde001ad02672cbe1310228a598151bfbbcd7ec0188a35f`](https://sepolia.etherscan.io/tx/0xd8076df6138369617dde001ad02672cbe1310228a598151bfbbcd7ec0188a35f) |
| Deploy PredictionMarket | [`0xf2eb2550106a313e808129d4c84a1c11ae559c9ef87252f585aecb34e19ac81b`](https://sepolia.etherscan.io/tx/0xf2eb2550106a313e808129d4c84a1c11ae559c9ef87252f585aecb34e19ac81b) |
| Propose market administration transfer | [`0x2d309da8856d91e4411f31f46fd81480580c8e6aeeb27a4a17470bae6448eeb4`](https://sepolia.etherscan.io/tx/0x2d309da8856d91e4411f31f46fd81480580c8e6aeeb27a4a17470bae6448eeb4) |
| Propose registry administration transfer | [`0x5f2abaf1ae8093fbcd98a5b9877053e605ca236f2143e554e752756ce94c6436`](https://sepolia.etherscan.io/tx/0x5f2abaf1ae8093fbcd98a5b9877053e605ca236f2143e554e752756ce94c6436) |

Raw receipts are under [receipts/](receipts/); [transactions.json](transactions.json) records
nonces, blocks, confirmation depth, gas, fees, and receipt paths.

## Safe setup: completed

Safe: `0xE33DDf0E7224245efe3D6BFcb39A78C22fbbAaac`, threshold **2 of 3**.
Owners are Benny, Matthew, and Adriel; their exact addresses are in the manifest.

The batch executed in block **12051344**:
[`0x89d8949a8cfaa91bfbd44345d8830470a5ddfbc001e346907ad4ec8f964ff69e`](https://sepolia.etherscan.io/tx/0x89d8949a8cfaa91bfbd44345d8830470a5ddfbc001e346907ad4ec8f964ff69e).
Its [receipt](receipts/07-safe-setup-0x89d8949a8cfaa91bfbd44345d8830470a5ddfbc001e346907ad4ec8f964ff69e.json)
and [post-setup verification](setup-verification.json) confirm Safe `ExecutionSuccess` and all
**15 zero-value inner CALLs**. The executed calldata exactly matches [safe-setup.json](safe-setup.json)
and the previously reviewed Solidity `SafeSetupPlan.calls(...)` output.
The saved batch is an execution record and must not be replayed.

1. Market `acceptAdministration()`.
2. Registry `acceptAdministration()`.
3. Grant `REGISTRAR_ROLE` to `0xFfb7c2D7B39A3da503Ef30761CCD1B19B767eDaa`.
4. Grant `PROPOSER_ROLE` to `0x137F79Cc7eA5c59Fa66bc09351b5f9331225c0Df`.
5. Add the new PredictionMarket as a consumer of the Safe-owned VRF subscription.
6. Activate R01–R10 in ResolverRegistry.

The batch checksum is:

```text
0xd68da08cc9a7fcecbdb9cdd9d6fcfb0ec9806c6a0f95bcb2b07f5c2685b3e8a2
```

Verification confirmed both admins equal the Safe, both pending admins are zero, the former
deployer has lost direct default administration, and each operational account has only its intended
registrar/proposer role. The VRF consumer and exact ten-address resolver pool are active.
The checked-in `VerifyAdministration.verify(...)` also returned `true` in a read-only RPC call
using its compiled runtime. Safe ownership remains Benny/Matthew/Adriel with a 2-of-3 threshold.

## VRF and verification evidence

- Coordinator: `0x9DdfaCa8183c41ad55329BdeeD9F6A8d53168B1B`.
- Subscription ID, stored as a decimal string:
  `43360769431604264970977939572487330506316889248276568284147859733693920197182`.
- Subscription owner: the Safe; balance at verification: **10 LINK**.
- Key hash: `0x787d74caea10b2b357790d5b5247c2f63d1d91572a9846f780606e4d953677ae`.
- Callback gas: `2000000`; confirmations: `3`; LINK billing.
- [verification.json](verification.json): canonical successful receipts, live runtime hashes,
  immutable getters, and pending role/admin/consumer state at block 12051243.
- [setup-verification.json](setup-verification.json): the completed authority/role/consumer/pool
  checks and exact executed-batch comparison at block 12051383. The market count and VRF request
  count were both zero at that snapshot; live market acceptance has not yet been demonstrated.
- [preflight-checks.json](preflight-checks.json): successful formatting/build, 119 tests with the
  full invariant budget, exact ABI/source/runtime checks, and independent pricing references.
- [callback-gas-probe.json](callback-gas-probe.json): read-only RPC state-override checks using
  the actual deployed runtime and ten resolver addresses. Both rounds and three random-word
  values succeeded within 2,000,000 gas; maximum top-level estimate was **774547**.
  These synthetic checks are not a real Chainlink fulfillment or a live market journey.
- [build.snapshot.json](build.snapshot.json): the immutable snapshot of the reviewed local build
  record. Live addresses belong to the deployment manifest, not that compiler-template record.

## Gas-estimation incident and recovery

The initial broadcast preparation encountered a transient RPC block-hash lookup error before
submitting anything. A retry on a confirmed fork block submitted nonce 27, but the token creation
exhausted its **551804** local-estimate gas limit. The node's live estimate was **2885548**.
The failed transaction was
[`0x020bfbd1c3f93815b51a817219e8814e46119014ec78c679ff2c76069ff3355f`](https://sepolia.etherscan.io/tx/0x020bfbd1c3f93815b51a817219e8814e46119014ec78c679ff2c76069ff3355f).
It created no contract; its receipt is preserved with status 0.

After reconciling receipts, code, and the nonce, the six-step plan was regenerated at nonces
28–33. The successful transactions used the exact reviewed bytecode/calldata with fresh live
`eth_estimateGas` and 30% headroom before each submission. Current Sepolia state-creation costs
are substantially higher than the pinned local Cancun simulation's gas accounting. Do not use
the old local fee estimate or blindly resume the failed Forge broadcast record.

- Successful deployment fees: **0.049935652749034780 Sepolia ETH**.
- Failed creation fee: **0.000551804000000000 Sepolia ETH**.
- Total deployment-attempt fees: **0.050487456749034780 Sepolia ETH**.

M4 acceptance still requires real evidence-backed fixture/result operations, an actual VRF request
and callback, lifecycle transaction smoke, and frontend/backend integration.
