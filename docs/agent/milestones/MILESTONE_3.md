# Milestone 3: MVP

Status: in progress — Sepolia contract deployment and guarded-buy smoke test complete; hosted indexer/API and frontend acceptance pending.

## Course Goal

Deliver a live minimum viable product that implements the core feature end to end, explain implementation design choices, and show the testing approach. Repository artifacts must include the working MVP, design documentation updated from Milestone 2, and an initial test suite or documented test plan.

## Repository Assessment

The `dev` branch now contains these components:

- a React frontend with Coinbase Wallet support and an Ethereum Sepolia contract read
- `ACONTestToken` plus a `PredictionMarket` contract integrating the bounded LMSR library for subsidy-funded market creation, quotes, guarded buys, positions, and events
- a FastAPI backend with indexed market/trade/status APIs, database migrations, and an RPC/ABI indexer worker; sample-match rows remain fallback data

Contract implementation commit `4c57dc0` merged in PR #16 and was deployed from merge commit `6e30d516669e51d7f3e4bff0d8670168da9b1f83`. Both ACON and PredictionMarket are live, market `0` is seeded, and a ten-share YES buy passed exact payment/position/event checks. The compiled ABI handoff is published in PR #19 and passes the backend validator. The frontend still points at M2; hosted indexing/database/API and frontend acceptance remain required. Sells, oracle proposals, challenges, resolver voting, settlement, and payouts are deferred.

Ethereum Sepolia (chain ID `11155111`) is the selected testnet for Milestone 3. Do not plan a Base Sepolia migration during MVP integration.

### Recorded deployment and trade

- Canonical manifest: [`deployments/sepolia-m3.json`](../../../deployments/sepolia-m3.json); exact-build ABIs are versioned under `deployments/abi/`.
- Market deployment/start block: `11963761`; demo market ID: `0`; confirmation depth: `2`.
- Successful buy: [`0xe5f5ff239ff3939cfc34c1c7719f2b1db9ef83d75f77f501236d004cb2d10c16`](https://sepolia.etherscan.io/tx/0xe5f5ff239ff3939cfc34c1c7719f2b1db9ef83d75f77f501236d004cb2d10c16), block `11964663`, log index `104`.
- Bought ten YES shares for `5249584441082326050` ACON base units (5.24958444108232605 ACON), equal to the submitted `maxCost`.
- [Receipt, raw log, and balance evidence](../../../contracts/deployments/sepolia-m3-2026-10-21/guarded-buy.json) was verified after two confirmations; the real backend RPC client/ABI decoder also decoded the canonical creation and trade events.
- Market `0` trading deadline: **2026-10-28 17:01:12 UTC**. A later trading demo needs a new funded market. Existing receipts remain usable for read-only indexing checks.

## MVP Definition

The required vertical slice is:

```text
User requests a buy quote
  -> wallet submits a guarded YES/NO buy on Ethereum Sepolia
  -> transaction is mined and emits TradeExecuted
  -> indexer processes the confirmed event exactly once
  -> PostgreSQL stores the derived market/trade projection
  -> FastAPI returns the indexed state
  -> frontend distinguishes submitted, mined, and indexed states
```

Market creation may be included in the demo, but a confirmed buy is the core acceptance path because trading/LMSR is the principal technical risk identified in Milestone 2 feedback.

AC_ON uses an on-chain binary LMSR automated market maker funded by creator subsidy. LMSR arithmetic uses 1e18 fixed-point precision, `b = 50` (`50e18` base units), and a minimum creator subsidy of `ceil(b * ln(2))`: `34,657,359,027,997,265,471` base units, or approximately `34.657359` test tokens. Market creation must revert atomically when the subsidy is insufficient. Trading and platform fees are not part of the planned product scope.

## Scope By Owner

| Owner | Milestone 3 responsibility |
|---|---|
| Benny | Core market lifecycle and guarded-buy contract integration, authorization, event emission, Ethereum Sepolia deployment, Foundry tests, and contract CI. |
| Matthew | Implement `LMSR.sol` with 1e18 precision, `b = 50`, the `ceil(b * ln(2))` subsidy rule, quote/cost accounting, and Foundry unit/fuzz/invariant tests. |
| Adriel | Market UI and Web3 integration, quote/buy flow, wallet transaction states, indexed-state refresh, and frontend tests. |
| Yudhveer | Event indexer, derived PostgreSQL schema, FastAPI read API, checkpoint/reorg recovery, mock oracle boundary, resolver projections, backend tests, and architecture/trust documentation. |
| Team | Freeze cross-layer interfaces, run an integrated demo, and reconcile presentation claims with the repository. |

Benny owns the authoritative on-chain resolver registry, selection, conflict checks, quorum, voting, and finalization contracts. Yudhveer owns the corresponding event projections, read APIs, operational status, and trust documentation; PostgreSQL must never select resolvers or decide outcomes. For Milestone 3, only the resolver boundary and projection design are required. Complete resolver execution remains Milestone 4 scope unless the trading slice finishes early.

## Interface Freeze Required Before Implementation

Names below are approved integration requirements. The guarded-buy functions/events are now implemented on this branch; the [contracts README](../../../contracts/README.md) records their exact ABI and error behavior. Changes still require team review and corresponding updates across every consumer.

The approved decision record is [`../interfaces/M3_TRADING_INTERFACE.md`](../interfaces/M3_TRADING_INTERFACE.md). It defines the payment asset, enum order, LMSR boundary, funding flow, ABI/events, revert contract, confirmation policy, validated numeric limits, and deployment handoff. Implementation PR [#13](https://github.com/yuddy-s/AC_ON-esports-prediction-market/pull/13) supplies the pinned dependency and validation evidence for the numeric policy.

### Contract reads and writes

| Interface | Minimum behavior |
|---|---|
| `getMarket(marketId)` | Returns stable market identifiers, question/match reference, deadline, state, creator, and LMSR quantities required by the UI/API. |
| `quoteBuy(marketId, outcome, shares)` | Returns the current maximum-precision cost using the same arithmetic as execution. |
| `buy(marketId, outcome, shares, maxCost)` | Executes only before the deadline and reverts if actual cost exceeds `maxCost`; emits `TradeExecuted`. |
| `balanceOf(marketId, account, outcome)` | Returns the authoritative on-chain YES or NO position. |

The write must contain an explicit slippage guard. A frontend-only quote is not sufficient because the price can change before mining.

Implementation handoff note: `getMarket` currently returns six values: question, deadline, state, creator, YES quantity, and NO quantity. The stable market ID is supplied as its argument and emitted in events, rather than returned. Confirm this representation of the identifier requirement with the frontend/backend reviewers before integration; the approved decision record is unchanged.

### Events required by the Milestone 3 indexer

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

All share, quantity, and cost values use 1e18 fixed-point base units. The ABI handoff must identify any value that uses a different unit. Every event projection also records chain ID, contract address, block number, block hash, transaction hash, and log index from the Ethereum log envelope.

Future resolution events should follow the same projection model:

- `OutcomeProposed`
- `MarketChallenged`
- `ResolversSelected`
- `ResolverVoteCast`
- `MarketFinalized`
- `MarketVoided`
- `PayoutClaimed`

These names and fields remain blocked on the resolution contract design and are not required for the trading MVP.

### FastAPI read API

| Endpoint | Purpose | MVP status |
|---|---|---|
| `GET /health` | Process and database health. | existing; extend with indexer status separately |
| `GET /api/markets` | Paginated indexed markets, optionally filtered by state. | required |
| `GET /api/markets/{market_id}` | Indexed market details plus projection metadata. | required |
| `GET /api/markets/{market_id}/trades` | Paginated confirmed trade history. | required |
| `GET /api/trades/by-transaction/{transaction_hash}` | Confirmed indexed trades for a mined wallet transaction; empty `items` until matching logs are indexed. | implemented for frontend synchronization |
| `GET /api/indexer/status` | Chain ID, contract address, latest observed block, safe checkpoint, and lag. | required |

The backend does not submit user trades. Users sign contract transactions through their wallets. API responses must identify indexed/derived data and include enough checkpoint information for the frontend to avoid presenting it as immediate authoritative state. The status response also includes `updated_at` so the frontend can detect a stalled worker even when reported block lag is zero. See the [backend frontend handoff](../APPLICATION_ROADMAP.md#frontend-backend-api-handoff) for the polling sequence.

The [public Sepolia deployment manifest](../../../deployments/sepolia-m3.json) is populated and validated. Once the persistent worker and API are configured, Yudhveer's read-only smoke script can compare the recorded creation/trade events with confirmed API projections. The [deployment runbook](../DEPLOYMENT_RUNBOOK.md) supplies the concrete worker configuration and validation command.

### Oracle boundary

Implement the oracle behind a provider interface only after the on-chain proposal/challenge interface is frozen:

```text
ResultProvider.fetch_result(external_match_id)
  -> PENDING | FINAL(outcome, evidence_reference) | VOID | UNAVAILABLE

OracleProposalService
  -> validates provider agreement/finality
  -> requests a least-privilege signer to call proposeOutcome
  -> records attempts and transaction state without treating them as settlement
```

Milestone 3 may use a deterministic mock provider. No public endpoint should accept an arbitrary outcome and sign it. Result fetching and transaction signing must be separate components. The oracle key must be server-side, use only the proposer role, and have a documented rotation/revocation procedure before hosted deployment.

### Resolver boundary

Resolution remains authoritative on-chain. PostgreSQL may project resolver selections and votes but must never select resolvers or decide the winning outcome independently.

Before resolver implementation, the team must decide:

- the eligible resolver set and admission/removal rules
- the manipulation-resistant randomness source
- exclusions for creator, proposer/oracle, challenger, and other conflicts
- behavior when fewer than five eligible resolvers exist
- voting deadline and terminal fallback when three matching votes are not reached
- EIP-1271 handling if Coinbase Smart Wallet accounts may act as resolvers

The actor who raises a valid dispute is the challenger and must not serve on that dispute's resolver committee.

## Derived Database Plan

Minimum tables or equivalent models:

| Projection | Key requirements |
|---|---|
| `indexed_contracts` | Chain ID, contract address, deployment/start block, ABI version. |
| `indexer_checkpoints` | Next block or last safely processed block plus its hash. |
| `processed_logs` | Unique `(chain_id, transaction_hash, log_index)` identity, block number/hash, event name. |
| `markets` | Contract-scoped market ID, indexed fields, state, source block, update transaction. |
| `trades` | Immutable trade facts and the Ethereum log identity. |

The current `sample_matches` table may remain temporarily for the Milestone 2 fallback, but new MVP endpoints must query indexed tables. Remove or clearly deprecate sample endpoints after the frontend switches.

### Replay and reorganization rules

1. Read logs in bounded block ranges from the configured deployment block.
2. Apply each range and advance its checkpoint in one database transaction.
3. Make duplicate delivery a no-op through the processed-log unique key.
4. Index only after a configurable confirmation depth for normal reads.
5. Store block hashes and compare the checkpoint ancestry before advancing.
6. On a mismatch, roll back projections derived from the fork point and replay canonical logs.
7. Provide a rebuild operation that can recreate all derived tables from chain events without writing to the contract.

PostgreSQL deletion or corruption must not affect authoritative contract state.

## Implementation Order

1. **Decision and interface freeze**
   - confirm Ethereum Sepolia as the milestone network
   - freeze enum names/order, event fields, payment asset, and slippage/revert behavior while retaining the approved 1e18 precision, `b = 50`, and subsidy rule
   - record contract address, deployment block, ABI version, and RPC configuration handoff
2. **Contract trading risk first**
   - implement quote and minimal guarded buy
   - emit complete deterministic events
   - add unit, fuzz, and accounting/invariant tests
3. **Indexer and database projection**
   - add schema migrations
   - implement idempotent backfill/live polling and safe checkpoints
   - add duplicate, restart, stale-state, and reorganization tests
4. **FastAPI indexed reads**
   - expose market, trade, and indexer-status endpoints
   - preserve explicit derived-state metadata
5. **Frontend integration**
   - show quoted cost and slippage protection
   - distinguish submitted, mined/reverted, and indexed states
   - refresh from chain while waiting for the derived API to catch up
6. **Oracle seam**
   - add deterministic provider tests and a signer abstraction only after `proposeOutcome` is stable
   - real esports API integration is optional for the MVP
7. **Resolver seam**
   - document and test projection handlers when resolution events exist
   - defer complete committee behavior until the protocol decisions above are approved

## Initial Test Plan

### Contracts / Foundry

- quote and execution use identical fixed-point arithmetic
- YES buying increases YES price monotonically
- insufficient subsidy causes atomic market-creation failure
- insufficient balance/payment and expired deadline revert
- stale quote exceeding `maxCost` reverts
- event values match post-trade contract state
- no negative balances and bounded market-maker loss

Current validation: 39 Foundry tests passed, including the pure LMSR invariant suite; the deployed runtime bytecode and live ten-share YES buy also passed verification. The market slippage test supplies a maximum below the current quote; an intervening-trade stale-quote scenario, callback/reentrancy tests, failed-token-transfer rollback tests, and multi-market accounting tests remain coverage follow-ups. The live contract smoke test does not establish hosted database/indexer/API or frontend acceptance.

### Backend, indexer, and oracle / Pytest

The current backend suite passed 52 tests. The completed manifest passes the handoff validator, and canonical live creation/trade retrieval and decoding passed separately. Persistent hosted projections and the read-only API smoke check remain pending; oracle provider/signer cases below are still planned scope.

- duplicate log delivery changes projections once
- restart resumes from the stored safe checkpoint
- missing ranges are replayed
- checkpoint block-hash mismatch triggers rollback/replay
- a full rebuild reproduces the same market/trade projections
- RPC timeout and partial-range failure do not advance the checkpoint
- API exposes only confirmed indexed trades and reports lag
- oracle provider pending, final, disagreement, unavailable, and retry paths
- signer failure does not record an outcome as proposed or finalized

### Frontend / Vitest and integration

- quote loading, stale-quote/slippage error, wallet rejection, revert, mined, and indexed states
- enum/status mapping matches Solidity exactly
- one integration test creates or loads a market, buys a position, indexes the event, and reads it through FastAPI

## Demo Acceptance Criteria

- [x] Code and docs identify Ethereum Sepolia consistently; the deployment manifest and integration configuration specify chain ID `11155111`.
- [x] Fresh deployment addresses, blocks, source revision, and exact-build ABIs are recorded in the public handoff.
- [x] One wallet submits a guarded YES buy (ten shares from the deployer EOA).
- [x] The mined transaction and `TradeExecuted` event are visible on Sepolia and verified after two confirmations.
- [ ] The persistent indexer stores the event once and reports its checkpoint.
- [ ] FastAPI returns the indexed trade and market projection from the hosted database.
- [ ] The frontend shows transaction confirmation separately from indexer completion.
- [ ] CI runs frontend build/tests, backend tests, contract format/build/tests, and the cross-layer integration test or a documented reproducible local equivalent. Current CI covers the frontend build, backend tests, and Foundry checks; full frontend/cross-layer acceptance remains.
- [ ] The presentation explains that PostgreSQL is derived and that the oracle cannot settle a challenged market.

## Explicitly Deferred Unless The Trading Slice Finishes Early

- production esports API integration
- full resolver registry, randomness, committee selection, and voting
- complete challenge, finalization, payout, and VOID accounting paths
- sell flow and advanced portfolio UX
- mainnet deployment or migration to another testnet

## Open Team Decisions

- keep the approved Milestone 3 trading interface decision record aligned with implementation
- approve or revise the PRBMath v4.2.2 pin and validated numeric policy supplied by LMSR implementation PR [#13](https://github.com/yuddy-s/AC_ON-esports-prediction-market/pull/13)
- select the operational Sepolia RPC provider while retaining the provider-neutral `SEPOLIA_RPC_URL` interface
- resolver randomness and liveness rules
- approved esports API and evidence format
