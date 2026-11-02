# Contract deployment handoff

## Current product build

**The current local build is a review draft, not a new Sepolia deployment.**

- `abi/PredictionMarket.abi.json`, `abi/ResolverRegistry.abi.json`, `abi/MarketPricing.abi.json`,
  `abi/ACONTestToken.abi.json`: exact current compiled ABIs.
- `build.json`: compiler settings, source/dependency hashes, ABI digests and runtime sizes.
  Runtime hashes describe compiler templates with immutable placeholders, not live bytecode hashes.
  Deployment addresses are null until a real deployment is recorded in a versioned manifest.
- `event-fixtures.anvil.json`: real local receipt logs, canonical signatures and decoded nonindexed
  values for required events, including a captured `ResolverSelectionRequestFailed` followed by
  successful retry recovery. Chain ID is **31337** and VRF is an explicit mock.
- `anvil-summary.json`: six contract journeys and their transaction/confirmation summary.

See the [ABI guide](../docs/agent/interfaces/CONTRACT_ABI.md),
[generated reference](../docs/agent/interfaces/CONTRACT_ABI_REFERENCE.md),
[test/security evidence](../docs/agent/testing/CONTRACT_VERIFICATION.md), and
[deployment runbook](../docs/agent/CONTRACT_DEPLOYMENT.md).

From `contracts/`, with Foundry and the pinned dependency present:

```bash
export FOUNDRY_OUT=out/current FOUNDRY_CACHE_PATH=cache/current
forge build
python3 script/smoke.py --start-anvil
python3 script/export_handoff.py
python3 script/export_handoff.py --check
```

Regenerate after source/configuration changes, review the resulting ABI/source differences and
obtain consumer/accounting approval. `--check` verifies exact ABI/source/runtime hashes, generated
reference and event examples; it does not establish approval or a live deployment.
The failed-request example is mandatory: generation and `--check` reject a fixture set that
omits it. Final ABI/source digest pinning remains a team approval gate after PR #38 reconciliation.

## Live deployment records

The current source replaces the older implementation, but an on-chain deployment's manifest and
source-versioned ABI remain immutable records. `sepolia-m3.json` identifies the previously deployed
buy-only market from source `6e30d516669e51d7f3e4bff0d8670168da9b1f83`; it is not the current lifecycle
contract. Its [deployment record](../contracts/deployments/sepolia-m3-2026-10-21/README.md) and
[guarded-buy receipt](../contracts/deployments/sepolia-m3-2026-10-21/guarded-buy.json) retain live evidence.
The legacy `sepolia-m3.template.json` is an unfilled template for that schema, not worker config.

The new deployment needs a consumer-reviewed manifest schema containing its full source commit,
chain ID, all four addresses/deployment receipts, ABI digests, Safe/roles, VRF config, resolver pool,
confirmation depth and example transactions. Current `build.json` content hashes are local build
evidence only. The backend's existing manifest validator targets the previously deployed interface;
its owners must update the schema/decoders before configuring it for the new market.

## Published ABI version convention

The unsuffixed ABI names describe the evolving current build. When publishing a **live** manifest,
save an immutable copy of each ABI under `deployments/abi/` using:

```text
<ContractName>.<first 12 characters of full source commit>.<first 12 characters of ABI file SHA-256>.abi.json
```

Record the full SHA-256 in the manifest. Published files are never edited/renamed after recording
their digest; repository-relative paths and LF line endings are part of the handoff. Pair every
address with its exact source-versioned ABI and deployment block. Keep credentials, RPC URLs,
private `.env` files and local broadcast output out of the public manifest.
