# Foundry contracts

The Foundry project is under `contracts/`. PR #16 merged the `4c57dc0` implementation of `PredictionMarket.sol` with Matthew's `LMSR.sol` and `ACONTestToken.sol` for creator-funded markets and guarded YES/NO buys into `dev`. Both contracts were deployed from merge commit `6e30d51`, and a live ten-share YES buy passed on Ethereum Sepolia. See the [deployment and trade record](deployments/sepolia-m3-2026-10-21/README.md) and [versioned integration manifest](../deployments/sepolia-m3.json). Hosted frontend/indexer/API acceptance remains pending.

The LMSR library uses 18-decimal fixed point values, `b = 50e18`, and PRBMath v4.2.2 pinned as a Git submodule. It accepts at most `2_000e18` outstanding shares per outcome and `100e18` shares per transaction. Prices sum exactly to `1e18`, accepted payments telescope exactly because quote cost is `C(after) - C(before)`, and no extra buy-cost rounding buffer is applied. A positive trade whose rounded cost does not increase is rejected as too small.

The older Ethereum Sepolia address is an M2 prototype and must not be used as the M3 deployment. Use the deployed addresses and exact-build ABIs in the versioned integration manifest above. The approved payment asset, LMSR boundary, public ABI, events, numeric validation, and deployment handoff are recorded in [`../docs/agent/interfaces/M3_TRADING_INTERFACE.md`](../docs/agent/interfaces/M3_TRADING_INTERFACE.md).

## Implemented behavior

- `ACONTestToken` has name `ACON Test Token`, symbol `ACON`, and 18 decimals. It has no monetary value, transfer fees, or rebasing behavior. Any address, including a smart wallet, can call `faucet()` once per token deployment for `1_000e18` units (1,000 ACON). There is no admin mint, faucet reset, or identity-based restriction; the claim limit is per address.
- `PredictionMarket(address paymentTokenAddress)` fixes the payment token immutably. Deploy it with the supplied ACON token; the constructor rejects zero but does not certify arbitrary tokens as fee-free or 18-decimal.
- Anyone can create a market after approving the market contract to spend ACON. `createMarket` rejects an empty question or non-future deadline, collects exactly `34_657_359_027_997_265_471` ACON base units, and creates the next sequential market ID directly in `OPEN` with zero YES/NO quantities. A failed payment reverts the creation transaction.
- `quoteBuy` and `buy` use the same `LMSR.buyCost` path. Both require an existing `OPEN` market, a deadline strictly in the future, and a supported share amount. `buy` recalculates the cost and reverts if it exceeds `maxCost`; it transfers only the actual cost from the caller, credits the caller's position, updates quantities/collateral accounting, and emits `TradeExecuted` atomically. There is no buy-on-behalf-of parameter.
- `createMarket` and `buy` share a reentrancy guard. Transfers occur before market/position updates under that guard. Sepolia ETH is used for gas only; these functions are nonpayable.
- The stored state remains `OPEN` after the deadline, but quotes and buys revert at or after that deadline. Clients must check both state and deadline. M3 has no explicit close transition.

Sells, share transfers, settlement, payout claims, subsidy withdrawal, complete VOID accounting, oracle signing, and resolver execution are deferred. ACON collected by markets stays in the contract for this milestone.

## ABI and event handoff

Use the ABI from the exact build being deployed. Solidity enums are `uint8` in the ABI. Economic values are integer `1e18` base units (`1e18` = one share or one ACON); deadlines are Unix seconds and market IDs/counts are unscaled integers.

| Public interface | Result / behavior |
|---|---|
| `paymentToken()` | Immutable ACON address. |
| `REQUIRED_SUBSIDY()` | Exact creator subsidy in ACON base units. |
| `marketCount()` | Number of sequential markets, starting with ID `0`. |
| `createMarket(string question, uint256 tradingDeadline)` | Returns the new `uint256 marketId`; requires token approval. |
| `getMarket(uint256 marketId)` | Returns `(string question, uint256 tradingDeadline, uint8 state, address creator, uint256 yesQuantity, uint256 noQuantity)`. |
| `quoteBuy(uint256 marketId, uint8 outcome, uint256 shares)` | Returns `uint256 cost` without changing state. |
| `buy(uint256 marketId, uint8 outcome, uint256 shares, uint256 maxCost)` | Returns `uint256 cost` and emits the executed trade. |
| `balanceOf(uint256 marketId, address account, uint8 outcome)` | Returns the account's shares; this is distinct from the token's `balanceOf(address)`. |

`getMarket` keeps the four M2 fields first and appends the two quantities. The ID is its lookup argument and the event key, not a returned field. Consumers must review this six-output ABI against the decision record's stable-identifier requirement. The per-market `collateralBalance` is internal accounting, not a public getter. `LMSR.prices` is an internal library method, not a public `PredictionMarket` endpoint.

Outcomes: `YES = 0`, `NO = 1`. Market states: `CREATED = 0`, `OPEN = 1`, `CLOSED = 2`, `PROPOSED = 3`, `DISPUTED = 4`, `FINALIZED = 5`, `VOID = 6`.

```solidity
event MarketCreated(
    uint256 indexed marketId,
    address indexed creator,
    string question,
    uint256 tradingDeadline
);

event TradeExecuted(
    uint256 indexed marketId,
    address indexed trader,
    uint8 indexed outcome,
    uint256 shares,
    uint256 cost,
    uint256 yesQuantity,
    uint256 noQuantity
);
```

Trade quantities are post-trade totals and `cost` is the amount actually collected. The indexer also needs the Ethereum log envelope (chain ID, contract address, block number/hash, transaction hash, log index). Use two confirmations for the default Sepolia demo. A mined transaction and an indexed trade are separate statuses.

### Reverts and limits

- Market validation: `EmptyQuestion`, `InvalidTradingDeadline`, `MarketNotFound`, `MarketNotOpen`, `TradingClosed`.
- Execution/payment: `SlippageExceeded(actualCost, maxCost)`, `InsufficientTokenBalance(required, available)`, `InsufficientTokenAllowance(required, available)`, `PaymentTransferFailed` (token returns false), and `ReentrantCall`. Token reverts propagate; the implementation expects ACON's boolean-returning transfer interface.
- LMSR errors propagate: `ZeroShares`, `TradeTooSmall`, `QuantityLimitExceeded`, and `TradeSizeLimitExceeded`.
- Out-of-range numeric outcomes are rejected by Solidity's enum ABI decoder before the function body; there is no custom `InvalidOutcome` error in this implementation. Consumers should validate outcomes and handle a generic revert rather than depend on a descriptive error string.

## Local checks

Requires Foundry (CI pins v1.8.3). From the repository root, initialize the already-pinned dependency if necessary:

```bash
git submodule update --init --recursive
```

Then run:

```bash
cd contracts
forge fmt --check
forge build
forge build script/Deploy.s.sol
forge test
```

The implementation's last local run reported 39 passing tests: 14 market tests, four token tests, 20 LMSR deterministic/fuzz tests, and the grouped LMSR invariant suite (256 runs, depth 500, 128,000 calls). The invariant coverage is for Matthew's pure LMSR handler, not a stateful token/market integration harness.

Market tests cover creation/subsidy collection, metadata, YES/NO buys, payment/position changes, deadline rejection, and `maxCost` rejection. The test named `testStaleQuoteExceedingMaxCostRevertsAtomically` sets `maxCost` below the current quote; it does not simulate a competing transaction changing the quote. Callback/reentrancy attacks, false-returning-token failures, multi-market accounting, and a full cross-layer buy demo still need additional validation. Foundry lint suppressions explain intended timestamp checks and guard-protected token calls; they are not a security audit.

CI already runs formatting, build, deployment-script compilation, and tests with recursive submodules on PRs to `dev`/`main`. The contract commit did not add a new CI job. The deployment script and README smoke-test sequence were also exercised on a temporary local Anvil chain: seed reads, faucet claim status, ten-share YES and NO buys, positions, exact ACON charges, and JSON ABI exports passed. This is contract-level local verification, not a frontend/indexer test or a Sepolia deployment.

## Ethereum Sepolia deployment

The existing M3 deployment is recorded above. Its initial script broadcast underestimated live token-creation gas; recovery used the RPC's `eth_estimateGas` plus 20% per transaction. See the [recovery record](deployments/sepolia-m3-2026-10-21/README.md#gas-estimation-recovery) before repeating deployment. Inspect receipts and pending nonces after any partial failure; a successful local simulation alone does not validate the live gas limit.

The following commands assume a terminal in `contracts/`, with Foundry on `PATH`. Create a local `.env` from `.env.example` if you do not already have one; set `SEPOLIA_PRIVATE_KEY` and `SEPOLIA_RPC_URL` locally. The deployer needs Ethereum Sepolia ETH for gas.

Load the configuration, verify chain ID `11155111`, and simulate first:

```bash
set -a
source .env
set +a
export PATH="$HOME/.foundry/bin:$PATH"
test "$(cast chain-id --rpc-url "$SEPOLIA_RPC_URL")" = "11155111" || exit 1
forge script script/Deploy.s.sol:DeployPredictionMarket \
  --rpc-url "$SEPOLIA_RPC_URL"
```

After reviewing the simulation, broadcast the deployment:

```bash
forge script script/Deploy.s.sol:DeployPredictionMarket \
  --rpc-url "$SEPOLIA_RPC_URL" \
  --broadcast
```

The script sends five transactions: deploy ACON, deploy PredictionMarket with that token, claim the deployer's faucet allocation, approve the exact subsidy, and create market `#0`. The seeded question is “Will Team A beat Team B?” with a deadline seven days after the script's simulated block time. This script does not execute a buy. Re-running it starts a new deployment; if a broadcast fails partway, inspect its receipts before retrying.

Save the two returned addresses and transaction receipts from `broadcast/Deploy.s.sol/11155111/run-latest.json`. Set these public values in the same terminal, replacing the placeholders:

```bash
export ACON_TOKEN_ADDRESS=0xYOUR_NEW_TOKEN_ADDRESS
export PREDICTION_MARKET_ADDRESS=0xYOUR_NEW_MARKET_ADDRESS
DEPLOYER=$(cast wallet address --private-key "$SEPOLIA_PRIVATE_KEY")
```

Read market `#0` with:

```bash
cast call "$PREDICTION_MARKET_ADDRESS" \
  'getMarket(uint256)(string,uint256,uint8,address,uint256,uint256)' 0 \
  --rpc-url "$SEPOLIA_RPC_URL"
```

Check the immutable token address and seed count:

```bash
cast call "$PREDICTION_MARKET_ADDRESS" 'paymentToken()(address)' --rpc-url "$SEPOLIA_RPC_URL"
cast call "$PREDICTION_MARKET_ADDRESS" 'marketCount()(uint256)' --rpc-url "$SEPOLIA_RPC_URL"
```

Expected seed: count `1`, state `1` (`OPEN`), creator equal to the deployer, zero YES/NO quantities, and the exact subsidy held by PredictionMarket. The deployer has already claimed the faucet and spent the subsidy; a second faucet claim from that address will revert.

## Guarded-buy smoke test

Use the deployed addresses above and a funded Sepolia wallet. This example uses `SEPOLIA_PRIVATE_KEY` as the buyer. For a different wallet, load that key locally; never pass it to the frontend or indexer. Claim only if this address has not already done so:

```bash
BUYER=$(cast wallet address --private-key "$SEPOLIA_PRIVATE_KEY")
if [ "$(cast call "$ACON_TOKEN_ADDRESS" 'hasClaimedFaucet(address)(bool)' "$BUYER" --rpc-url "$SEPOLIA_RPC_URL")" = "false" ]; then
  cast send "$ACON_TOKEN_ADDRESS" 'faucet()' \
    --private-key "$SEPOLIA_PRIVATE_KEY" --rpc-url "$SEPOLIA_RPC_URL"
fi
```

Quote ten YES shares, approve exactly that cost, and submit a guarded buy. The quote call deliberately omits its return type to get raw hex, then `cast to-dec` converts it to an integer without scientific-notation annotations:

```bash
SHARES=10000000000000000000
OUTCOME=0
COST_HEX=$(cast call "$PREDICTION_MARKET_ADDRESS" \
  'quoteBuy(uint256,uint8,uint256)' 0 "$OUTCOME" "$SHARES" --rpc-url "$SEPOLIA_RPC_URL")
MAX_COST=$(cast to-dec "$COST_HEX")
cast send "$ACON_TOKEN_ADDRESS" 'approve(address,uint256)' \
  "$PREDICTION_MARKET_ADDRESS" "$MAX_COST" \
  --private-key "$SEPOLIA_PRIVATE_KEY" --rpc-url "$SEPOLIA_RPC_URL"
cast send "$PREDICTION_MARKET_ADDRESS" 'buy(uint256,uint8,uint256,uint256)' \
  0 "$OUTCOME" "$SHARES" "$MAX_COST" \
  --private-key "$SEPOLIA_PRIVATE_KEY" --rpc-url "$SEPOLIA_RPC_URL"
cast call "$PREDICTION_MARKET_ADDRESS" 'balanceOf(uint256,address,uint8)(uint256)' \
  0 "$BUYER" "$OUTCOME" --rpc-url "$SEPOLIA_RPC_URL"
cast call "$ACON_TOKEN_ADDRESS" 'balanceOf(address)(uint256)' "$BUYER" --rpc-url "$SEPOLIA_RPC_URL"
```

For a fresh buyer position, expect `10e18` YES shares and an ACON decrease equal to the executed cost, not ten fixed-price credits. Change `OUTCOME` to `1` for NO. Another trade can change the quote before mining; a cost above `MAX_COST` reverts, in which case request a fresh quote and approval. Once the deadline passes, use a newly created market. Record the successful buy receipt and its post-trade `TradeExecuted` log.

## Deployment handoff to Adriel and Yudhveer

Generate JSON ABIs from the exact deployed source:

```bash
forge inspect PredictionMarket abi --json
forge inspect ACONTestToken abi --json
```

The current [integration manifest](../deployments/sepolia-m3.json) records deployed source `6e30d516669e51d7f3e4bff0d8670168da9b1f83`, chain ID `11155111`, both checksummed addresses, deployment transactions/blocks, versioned ABI paths/hashes, demo market ID, confirmation depth, and successful creation/buy transactions. For future deployments, record the exact source revision and actual receipts, and follow the [ABI filename convention](../deployments/README.md#abi-version-convention). The [deployment/trade record](deployments/sepolia-m3-2026-10-21/README.md) documents enum order, units, and executed checks. The backend uses `PREDICTION_MARKET_ADDRESS`, `PREDICTION_MARKET_DEPLOYMENT_BLOCK`, and `PREDICTION_MARKET_ABI_PATH`; see the [deployment runbook](../docs/agent/DEPLOYMENT_RUNBOOK.md).

Adriel must use the published addresses/ABIs, add ACON faucet/approval and quote/buy flows, and retain the market ID from the lookup/event (it is not a `getMarket` return field). The backend handoff validator and live RPC/ABI decoding checks passed; Yudhveer still needs to verify persistent hosted projections and their API responses. Consumer review of the six-output identifier representation remains a team follow-up. The existing M2 frontend still needs the new address and ABI applied together during integration.

Do not commit private keys, `.env`, `broadcast/`, or compiler output. Never deploy this demo contract to mainnet.
