# Foundry contracts

This directory contains the current prediction-market product. Contracts live directly in `src/`,
tests in `test/`, and deployment/check tooling in `script/`. The current lifecycle implements the
[approved feature-complete design](../docs/agent/interfaces/M4_FEATURE_COMPLETE_INTERFACE.md).
The implementation and exact ABI/economic proof are merged in PRs #37/#38 and locally verified. A fresh Sepolia deployment, Safe/VRF setup, and role handoff are pending.

## Source layout

| File | Responsibility |
|---|---|
| `src/PredictionMarket.sol` | Registered fixtures, user-funded markets, buys/sells, proposals/challenges, VRF committee selection, voting/timeouts, settlement, claims and creator surplus |
| `src/MarketAccess.sol` | Registrar/proposer roles and two-step administration transfer |
| `src/ResolverRegistry.sol` | Safe-administered resolver allowlist |
| `src/MarketPricing.sol` | Stateless mathematical ceiling-buy / floor-sell quotes and input limits |
| `src/LMSRBounds.sol` | Directed numerical intervals that certify mathematical trade rounding |
| `src/LMSR.sol` | Bounded fixed-point cost/price mathematics |
| `src/ACONTestToken.sol` | 18-decimal, fee-free test payment token; one 1,000 ACON faucet claim per address |
| `src/IERC20Minimal.sol` | Payment-token interface |
| `src/IVRFCoordinatorV2Plus.sol` | Chainlink VRF v2.5 request interface |

`PredictionMarket` is the single active market implementation. A fixture registrar establishes
Team A/YES and Team B/NO, start time, evidence and identity. A user approves the fixed subsidy
(`34657359027997265471` ACON base units), then creates one market for the fixture using its current
revision hash. Buys and sells use fresh quotes plus caller slippage limits. The market handles
immutable proposals, bonded challenges, five-resolver committees and terminal payout accounting.

Economic units are integers: `1e18` per ACON/share, `b=50e18`, maximum `100e18` per trade and
`2000e18` outstanding shares per side. Buys use the certified ceiling of the mathematical LMSR
cost increase; sells use the certified floor of the decrease. Nonnegative rounding residues remain
in collateral. Matthew's [economic proof and stateful invariants](../docs/agent/testing/M4_ECONOMIC_PROOF.md)
review solvency, claims, bonds, and surplus against this model; final approval remains required.
The exact current state enum, tuple layouts, errors and payment/claim rules are in the
[contract ABI guide](../docs/agent/interfaces/CONTRACT_ABI.md) and
[generated reference](../docs/agent/interfaces/CONTRACT_ABI_REFERENCE.md).

The [rounding correction](../docs/agent/testing/PRICING_ROUNDING.md) fixes the reported 464-base-unit
sell overestimate and pairs it with ceil-buy pricing to avoid reverse-trade gains. Independent
Decimal vectors certify the regression expectations. This numeric amendment remains under review.

## Local checks

Requires Foundry v1.8.3, Python 3.11+ and PRBMath v4.2.2 at the pinned submodule revision.
Initialize that dependency from the repository root if needed:

```bash
git submodule update --init --recursive
```

From `contracts/`:

```bash
export PATH="$HOME/.foundry/bin:$PATH"
export FOUNDRY_OUT=out/current FOUNDRY_CACHE_PATH=cache/current
forge fmt --check
forge build
forge build script/Deploy.s.sol
forge test
python3 script/export_handoff.py --check
python3 script/pricing_reference.py --check
python3 script/smoke.py --start-anvil
```

The source uses solc 0.8.24 with optimizer 200 and IR optimization. Tests are grouped by behavior:
`PredictionMarket.t.sol` exercises the real ACON integration, `MarketPricing.t.sol` covers independent
mathematical references and rounding boundaries, `MarketLifecycle.t.sol` covers fixture/
settlement rules, `Resolvers.t.sol` covers VRF/votes, `MarketSecurity.t.sol` covers adversarial accounting,
and `Deployment.t.sol` covers Safe setup. Token/math tests and the shared `MarketTestBase.sol` are in
the same folder. See the [verification report](../docs/agent/testing/CONTRACT_VERIFICATION.md) for results,
coverage limitations, static-analysis findings and CI commands.

## ABI and deployment handoff

`script/export_handoff.py` exports the current four production ABIs to `../deployments/abi/`, build
hashes to `../deployments/build.json`, and actual Anvil event examples to `../deployments/`.
Run the smoke before regenerating the handoff, then run the exporter with `--check`.

`script/Deploy.s.sol` is the current Sepolia deployment script. Use `contracts/.env.example` for
reviewed Safe/VRF/operational settings. It deploys token, pricing, registry and market, then proposes
Safe administration transfers. `SafeSetupPlan` builds the Safe calls; `VerifyAdministration` checks
the completed handoff. Follow the [deployment runbook](../docs/agent/CONTRACT_DEPLOYMENT.md) for
simulation, authorization, live checks and recovery.

The current source/ABI supersedes the previous buy-only implementation. Previously published
Sepolia receipts and source-versioned ABIs still describe those immutable deployed contracts:
[`../deployments/sepolia-m3.json`](../deployments/sepolia-m3.json) and its
[deployment record](deployments/sepolia-m3-2026-10-21/README.md). Reproduce them from their recorded
commit, not today's source. Consumers must update the contract address, ABI, enums and start block
together when integrating the current product. Current frontend/backend configurations still use
that previously deployed ABI until their owners complete the new-interface integration.
