# Milestone 3 Trading Interface Decision Record

Status: proposed for team review

This document is the proposed cross-layer contract for the Milestone 3 guarded-buy vertical slice. It becomes the implementation baseline when this decision PR is approved and merged. Code and tests remain the source of truth for implemented behavior; this document must be updated if validation forces a different bound, tolerance, or dependency version.

## Scope

Milestone 3 proves one guarded YES/NO buy end to end on Ethereum Sepolia:

```text
quote -> wallet submission -> mined TradeExecuted event
      -> confirmed indexer projection -> FastAPI -> frontend indexed state
```

The slice includes LMSR buy pricing, creator subsidy collection, payment-token transfers, positions, post-trade quantities, slippage protection, event indexing, and submitted/mined/indexed UI states. Sells, settlement, claims, complete VOID accounting, and resolver execution are deferred.

## Accepted Baseline

These values were already approved in the Milestone 3 plan and are not reopened by this proposal:

| Item | Value |
|---|---|
| Network | Ethereum Sepolia, chain ID `11155111` |
| Fixed-point scale | `WAD = 1e18` |
| Liquidity parameter | `B = 50e18` |
| Minimum creator subsidy | `34_657_359_027_997_265_471` payment-token base units |
| Subsidy rule | `ceil(b * ln(2))` |
| Trading/platform fees | None |

## Payment Asset

- Use a custom mintable 18-decimal ERC-20 named ACON Test Token (`ACON`).
- Sepolia ETH pays gas only. It is not the LMSR collateral or payout asset.
- `ACON` is testnet-only, has no real monetary value, and must not charge transfer fees or rebase balances.
- One winning `1e18` share is intended to redeem for `1e18` `ACON` base units when settlement is implemented.
- The `PredictionMarket` constructor receives the token address and stores it immutably, so every market in one deployment uses the same asset.
- The test-token deployment must expose a documented faucet or mint path for demo accounts.

## Enums And Lifecycle

The public outcome order is frozen across Solidity, ABI, events, backend, frontend, tests, and diagrams:

```solidity
enum Outcome {
    YES, // 0
    NO   // 1
}
```

The existing market-state order remains unchanged for Milestone 3:

```text
CREATED = 0
OPEN = 1
CLOSED = 2
PROPOSED = 3
DISPUTED = 4
FINALIZED = 5
VOID = 6
```

A market creation transaction must collect the full subsidy atomically and create the market directly in `OPEN`. Quote and buy operations require `OPEN` and `block.timestamp < tradingDeadline`; trading is closed at the exact deadline. Milestone 3 does not require a separate transaction or event that changes the stored state to `CLOSED`, so clients must treat an `OPEN` market at or after its deadline as not tradable. An explicit close transition and `CLAIMABLE` or other future states are deferred.

## LMSR Library Boundary

`LMSR.sol` is an internal, pure Solidity library. It contains no storage, ERC-20 transfers, user balances, deadlines, events, authorization, or lifecycle transitions. Tests call it through a small harness.

The proposed internal interface is:

```solidity
function cost(uint256 qYes, uint256 qNo) internal pure returns (uint256);

function buyCost(
    uint256 qYes,
    uint256 qNo,
    bool buyYes,
    uint256 shares
) internal pure returns (uint256);

function prices(
    uint256 qYes,
    uint256 qNo
) internal pure returns (uint256 yesPrice, uint256 noPrice);

function requiredSubsidy() internal pure returns (uint256);
```

`qYes` and `qNo` are non-negative total outstanding share quantities. Quantities, shares, prices, costs, and subsidy use `1e18` base units. Sells and negative quantities are not supported in this milestone.

Use the stable log-sum-exp form instead of two positive exponentials:

```text
m = max(qYes, qNo)
C(qYes, qNo) = m + b * ln(1 + exp(-abs(qYes - qNo) / b))
buyCost = C(after) - C(before)
```

## Fixed-Point Dependency

- Use PRBMath v4.2.2 at commit `4bb0a1b8788d16541d4b5148a94d5fc7dda1d4ab` for signed 59.18-decimal `exp` and `ln`; do not implement custom approximations.
- The compatibility spike in implementation PR [#13](https://github.com/yuddy-s/AC_ON-esports-prediction-market/pull/13) compiles the dependency against Solidity `0.8.24` and exercises it through deterministic, fuzz, and invariant tests.
- A moving branch such as `release-v4` is not an acceptable final pin.
- PRBMath is installed as a Forge Git submodule. GitHub Actions initializes submodules recursively, and `@prb/math/` maps to `lib/prb-math/`.
- The CI-pinned Foundry version is authoritative for merge validation. Local newer versions are acceptable only when the same changes pass CI.

## Validated Numeric Policy

Implementation PR [#13](https://github.com/yuddy-s/AC_ON-esports-prediction-market/pull/13) validates and freezes these values:

| Item | Frozen value | Rationale |
|---|---:|---|
| Maximum total quantity per outcome | `2_000e18` | Bounds `abs(qYes - qNo) / B` to `40`, below PRBMath's negative-exponent zero threshold. |
| Maximum shares per transaction | `100e18` | Bounds one transaction's normalized inventory movement to `2`. |
| Price-sum tolerance | `0` | One price is computed and the other is its complement, so the pair sums exactly to `1e18`. |
| Telescoping-cost tolerance | `0` for accepted trades | Every accepted payment is exactly `C(after) - C(before)`. |
| Positive buy-cost rounding buffer | `0` | No additive buffer is required for the bounded-loss invariant. Rounded non-increasing payments revert with `TradeTooSmall`. |

The PRBMath value for `C(0, 0)` is `34_657_359_027_997_265_450`, leaving the approved ceiling subsidy 21 base units higher. Zero shares revert. A positive share amount whose calculated payment does not increase the rounded potential reverts as a trade that is too small. Quote and execution call the same `buyCost` path and apply the same rounding policy.

## Creator Subsidy And Token Flow

- `createMarket` uses `transferFrom` to collect exactly `REQUIRED_SUBSIDY` from the creator.
- The creator must approve the market contract before creation.
- Insufficient balance, insufficient allowance, or a failed token transfer reverts the complete creation transaction.
- No partially funded market is stored and no `MarketCreated` event is emitted on failure.
- Subsidy is held by the market contract for the created market.
- A new market begins at `qYes = 0` and `qNo = 0`, with prices approximately `0.5e18` each.
- The Milestone 3 contract does not release subsidy because settlement and VOID execution are deferred.

## Public Contract Interface

The proposed public trading interface is:

```solidity
function quoteBuy(
    uint256 marketId,
    Outcome outcome,
    uint256 shares
) external view returns (uint256 cost);

function buy(
    uint256 marketId,
    Outcome outcome,
    uint256 shares,
    uint256 maxCost
) external returns (uint256 cost);

function balanceOf(
    uint256 marketId,
    address account,
    Outcome outcome
) external view returns (uint256 shares);
```

`getMarket(marketId)` must expose at least the stable identifier, question or match reference, trading deadline, state, creator, `yesQuantity`, and `noQuantity`. The immutable payment-token address is a contract-level read.

Both `quoteBuy` and `buy` require an existing, open, unexpired market and a supported positive share amount. `buy` recalculates current cost and reverts when `actualCost > maxCost`. Token transfer, position updates, quantity updates, and event emission are one atomic transaction.

## Events

The Milestone 3 event contracts are:

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

For `TradeExecuted`, `outcome` follows `YES = 0` and `NO = 1`; `cost` is the amount actually charged; and `yesQuantity` and `noQuantity` are post-trade values. All numeric economic values use `1e18` base units.

The event envelope handoff also includes chain ID, contract address, block number, block hash, transaction hash, and log index. The indexer uses `(chain_id, transaction_hash, log_index)` as the idempotency identity.

## Revert Contract

The implementation must expose stable custom errors or equivalently stable revert behavior for:

- Unknown market.
- Market not open.
- Trading deadline reached.
- Zero shares.
- Trade too small after fixed-point rounding.
- Quantity or per-transaction limit exceeded.
- Actual cost exceeding `maxCost`.
- Insufficient subsidy balance or allowance.
- Unsupported outcome if a raw numeric outcome reaches a boundary.

Frontend and integration tests must map these cases to user-facing states without parsing unstable free-form strings.

## Indexer And Deployment Handoff

- Confirmation depth is configurable; the proposed Sepolia demo default is two confirmations.
- RPC URLs and provider credentials are environment secrets. Code and documentation use `SEPOLIA_RPC_URL` and do not require a provider-specific implementation.
- A deployment handoff includes chain ID, market-contract address, token address, deployment/start block, ABI or commit SHA, enum order, confirmation depth, and demo market ID.
- The frontend distinguishes wallet submission, mining/revert, and indexer completion. A mined transaction is not yet indexed state.

## Merge Checks

Contract changes must pass the repository's pinned CI checks:

```text
forge fmt --check
forge build
forge build script/Deploy.s.sol
forge test
```

The LMSR implementation PR also runs deterministic tests, bounded fuzz/property tests, and the bounded-loss invariant. CI is pinned to 256 fuzz runs and 256 invariant runs at depth 500 (128,000 stateful calls). A supplemental local run of 10,000 cases per fuzz property passed against PRBMath v4.2.2; it supplements but does not replace CI.

## Explicitly Deferred Decisions

These decisions do not block the Milestone 3 guarded-buy slice:

- Sell pricing and negative inventory behavior.
- Settlement, claims, and at-most-once payout execution.
- Release or disposition of creator subsidy after finalization or VOID.
- Complete VOID accounting across terminal states.
- Resolver eligibility, admission, randomness, conflicts, quorum, non-votes, and timeout fallback.
- Oracle proposal/challenge implementation and real esports API selection.
- Mainnet deployment.

They remain Milestone 4 or later work unless the complete guarded-buy vertical slice finishes early.
