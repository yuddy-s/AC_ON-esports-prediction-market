# Milestone 3: MVP

Status: in progress

## Course Goal

Deliver a live minimum viable product that implements the core feature end to end, explain implementation design choices, and show the testing approach. Repository artifacts must include the working MVP, design documentation updated from Milestone 2, and an initial test suite or documented test plan.

## Repository Assessment

The guarded-buy branch now contains these components:

- a React frontend with Coinbase Wallet support and an Ethereum Sepolia contract read
- `ACONTestToken` plus a `PredictionMarket` contract integrating the bounded LMSR library for subsidy-funded market creation, quotes, guarded buys, positions, and events
- a FastAPI backend with indexed market/trade/status APIs, database migrations, and an RPC/ABI indexer worker; sample-match rows remain fallback data

Contract implementation commit `4c57dc0` is available for review. Foundry unit tests cover the ACON faucet/transfers, market funding, quote/buy behavior, slippage rejection, and deadlines; the existing pure LMSR fuzz/invariant suite also passes locally. The current Sepolia deployment is an earlier M2 prototype. A new ACON/market deployment, compiled-ABI handoff, and live buy-to-indexer-to-frontend validation are still required. No sell, oracle proposal, challenge, resolver voting, settlement, or payout behavior is implemented by this contract change.

Ethereum Sepolia (chain ID `11155111`) is the selected testnet for Milestone 3. Do not plan a Base Sepolia migration during MVP integration.

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
| `GET /api/indexer/status` | Chain ID, contract address, latest observed block, safe checkpoint, and lag. | required |

The backend does not submit user trades. Users sign contract transactions through their wallets. API responses must identify indexed/derived data and include enough checkpoint information for the frontend to avoid presenting it as immediate authoritative state.

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

Current validation: 39 tests passed in the last local Foundry run, including the pure LMSR invariant suite. The market slippage test supplies a maximum below the current quote; an intervening-trade stale-quote scenario, callback/reentrancy tests, failed-token-transfer rollback tests, and multi-market accounting tests remain coverage follow-ups. A successful local deployment simulation is not evidence of a live Sepolia or cross-layer demo.

### Backend, indexer, and oracle / Pytest

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

- all code and docs identify Ethereum Sepolia consistently
- a fresh deployment address and deployment block are recorded without committing secrets
- one wallet submits a guarded YES or NO buy
- the mined transaction and `TradeExecuted` event are visible on Sepolia
- the indexer stores the event once and reports its checkpoint
- FastAPI returns the indexed trade and market projection
- the frontend shows transaction confirmation separately from indexer completion
- CI runs frontend build/tests, backend tests, contract format/build/tests, and the cross-layer integration test or a documented reproducible local equivalent
- the presentation explains that PostgreSQL is derived and that the oracle cannot settle a challenged market

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
