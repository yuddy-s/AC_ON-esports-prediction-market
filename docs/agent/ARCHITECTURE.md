# AC_ON Architecture

AC_ON is a testnet-only decentralized esports prediction market. Users connect a Coinbase Wallet and trade YES/NO shares on binary esports match outcomes. The planned product is not fully trustless or fully permissionless: contract state should be authoritative for markets and payouts, while esports APIs, oracle automation, initial resolver bootstrapping, and indexing are trusted/off-chain support systems.

This document describes the repository as currently inspected. Do not treat planned components as implemented.

## Current Repo State

| Area | Status | Notes |
|---|---|---|
| Frontend | implemented | React + Vite + TypeScript app under `frontend/`. |
| Wallet | implemented | Coinbase Smart Wallet and injected wallet fallback through wagmi. |
| Chain config | implemented | Ethereum Sepolia (chain ID `11155111`) hosts both the older M2 prototype and the deployed M3 token/market pair. The frontend still needs the M3 address/ABI update. |
| Contracts | deployed and smoke-tested | ACON-funded creation, LMSR quotes, guarded buys, positions, and `TradeExecuted` are deployed from `6e30d51`. Market `0` and a ten-share YES buy are confirmed. |
| Backend | foundation | FastAPI app has health, deprecated sample-match endpoints, and paginated indexed market/trade/status reads. |
| Oracle | planned | No oracle service found. |
| Indexer | implemented; live decoding verified | Confirmed projections, checkpoints, rebuild/reorg recovery, RPC polling, and ABI decoding exist. Canonical live creation/trade decoding passed; hosted persistent indexing/API verification remains. |
| Database | schema prepared | Alembic revision `20261018_0001` was reported applied to Supabase on 2026-10-21, with empty indexer tables at that check. Hosted M3 projections remain to be verified; sample data remains non-authoritative fallback data. |
| CI | implemented | GitHub Actions runs frontend build, backend tests, and contract formatting/build/tests. |

## Current Diagram

```text
Implemented frontend prototype:
User Browser -> React / wagmi / viem -> connected wallet + M2 Sepolia read

Verified M3 contract path:
Funded EOA / Foundry -> ACON approval -> guarded buy on Sepolia
                                             |
                                             v
                                confirmed TradeExecuted log
                                             |
                                             v
                                backend RPC client + ABI decoder

Remaining live integration (components exist; deployment/UI work remains):
M3 quote/buy frontend -> wallet -> deployed M3 contracts
       |                                  |
       v                                  v
FastAPI indexed reads <- PostgreSQL <- persistent indexer worker

Future scope: oracle proposals, challenges, resolver voting, settlement, payouts.

Authoritative state: blockchain contracts
Derived state: PostgreSQL
```

## Frontend

Status: implemented, minimal prototype.

The frontend lives in `frontend/` and uses React, Vite, TypeScript, Tailwind, wagmi, viem, and Coinbase Wallet SDK. It currently supports wallet connection and balance display.

The app reads placeholder market `0` from the earlier Ethereum Sepolia deployment. M3 quote/buy UI and indexed-state transitions remain pending frontend integration.

## Contracts

Status: deployed M3 guarded-buy implementation; live contract smoke test passed.

`ACONTestToken` is an 18-decimal test ERC-20. Each address can call its permissionless `faucet()` once for 1,000 ACON. The immutable `paymentToken` in `PredictionMarket` is set at construction. Creation and buys pull ACON from `msg.sender` using the caller's token allowance; positions are also credited only to that caller. No native ETH is accepted by these operations.

Creation atomically collects the exact LMSR subsidy, allocates a sequential market ID, and initializes `OPEN` with zero quantities. Both `quoteBuy` and `buy` call `LMSR.buyCost`. Execution enforces `actualCost <= maxCost`, collects the actual payment, updates the caller's shares plus market quantities/collateral, and emits the frozen event. Both mutators hold a shared reentrancy guard across the token call. The constructor rejects a zero token address but relies on deployment to supply the intended ACON token.

The implementation's 39 Foundry tests pass, including the pure-math fuzz/invariant suite. Runtime bytecode matches the deployed build, and a live ten-share YES buy passed exact payment/position/event checks after two confirmations. The [contracts README](../../contracts/README.md) gives the deployed six-output `getMarket` ABI, revert behavior, commands, and coverage follow-ups. The hosted indexer/database/API and frontend integration are still required for the complete MVP. Sells, resolution, settlement, and payouts are deferred.

The implementation follows the approved M3 trading boundary: custom 18-decimal `ACON` test ERC-20, internal pure `LMSR.sol`, creator-funded subsidy, guarded buys with `maxCost`, and deterministic post-trade `TradeExecuted` values. See [`interfaces/M3_TRADING_INTERFACE.md`](interfaces/M3_TRADING_INTERFACE.md) for the frozen parameters and ABI contract.

## Backend

Status: indexed APIs implemented; hosted M3 acceptance pending.

The FastAPI service runs from `backend/` and exposes indexed markets, trades, transaction-hash lookup, and indexer status with freshness metadata. Health/sample-match endpoints remain from M2. It connects to PostgreSQL through `DATABASE_URL`; deployment and a live projection-to-API comparison are still required.

The sample matches are fake display data only. They are not on-chain markets and must not be treated as authoritative market state.

## Oracle

Status: planned.

No oracle service exists yet. Intended behavior: compare approved esports API results, propose outcomes on-chain when rules allow, route disagreements or timeouts to dispute/manual paths, and avoid unilateral settlement of disputed markets.

## Resolver Protocol

Status: proposed for team review; not approved or implemented.

Resolution remains authoritative on-chain. The proposal assigns an on-chain resolver allowlist to a project-team multisignature wallet and requires an event for every admission or removal. Registry changes apply to future committee selections; removal does not rewrite an active voting round. PostgreSQL may project registry, selection, vote, deadline, and outcome events, but it must never select resolvers or decide an outcome.

A challenged result or unusable oracle result opens the first committee-selection round. A first voting round without quorum opens one replacement selection round. Each selection round stores one fixed seven-day deadline when the round opens; retries cannot restart or extend that clock. Before the first VRF request, the contract snapshots the round's eligible, non-conflicted candidates. Registry changes after that snapshot apply only to later rounds, and retries reuse the same snapshot. The contract excludes the market creator, oracle proposer, challenger, and any address recorded on-chain as having traded in or holding a position in the market. These conflicts are enforceable only at the address level.

Chainlink VRF on Sepolia selects five distinct addresses from the snapshot. The contract tracks one current request ID per market and round; a retry replaces that ID without changing the snapshot or deadline. A callback may install a committee only when its request ID, market, round, selection state, and deadline are all current. Superseded, duplicate, mismatched, or late callbacks emit an ignored-fulfillment event and make no state change. If no five-address snapshot or valid committee exists by the fixed deadline, any account may trigger `VOID`.

Each selected resolver may cast one direct on-chain `YES`, `NO`, or `VOID` vote during a 48-hour round. Three matching votes finalize the result. If the first committee does not reach quorum, the replacement round takes a new candidate snapshot and excludes first-round resolvers when the eligible pool permits. Failure of the replacement round to reach quorum makes the market `VOID`.

Direct voting authorizes `msg.sender` and does not require off-chain signature recovery, including for Coinbase Smart Wallet transactions. A future relayed-vote feature must support ECDSA for externally owned accounts and EIP-1271 for contract wallets. Team approval of this proposal, contract interfaces, exact VRF retry delay/configuration, settlement, payouts, and complete `VOID` accounting are deferred to Milestone 4.

## Indexer

Status: worker implemented; live RPC/ABI decoding verified; hosted indexing pending.

The backend contains a provider-independent event indexer with normalized `MarketCreated` and approved `TradeExecuted` handlers. It persists a unique `(chain_id, transaction_hash, log_index)` event identity, checks range-end hashes before and after applying each batch, advances each bounded block range atomically with its checkpoint, waits for configurable confirmations, and rebuilds derived projections when the checkpoint block hash no longer matches the canonical chain. PR #15 added JSON-RPC retrieval/polling and the strict ABI decoder; PRs #17 and #18 added transaction lookup, freshness/replay checks, versioned handoff validation, and a read-only smoke command. The published manifest passes validation, and the real RPC client/decoder correctly reads both canonical demo events. Persistent hosted projections, restart/replay, and API reconciliation remain to be verified.

## Database

Status: schema migration reported applied; hosted live projections unverified.

Milestone 2 uses Supabase PostgreSQL as a hosted development database so teammates do not need local PostgreSQL. PostgreSQL should be treated as derived/indexed or demo display state. Blockchain state is authoritative.

## Deployment Status

Status: contracts live; hosted application integration pending.

The canonical [Sepolia manifest](../../deployments/sepolia-m3.json) records source `6e30d516669e51d7f3e4bff0d8670168da9b1f83`, ACON `0x315FCA0DDAA367446f36A3184D8f6b2Df76b5618`, and PredictionMarket `0x19EF739001038Ce9DFB1E12Cf45A10c9250A60a7`. The market deployment/start block is `11963761`; the indexer default is two confirmations. The [deployment/trade record](../../contracts/deployments/sepolia-m3-2026-10-21/README.md) includes receipts and exact-build ABIs.

The script's first token-creation broadcast exhausted its simulated gas limit. After inspecting the failed receipt, deployment completed through `forge create` and `cast send` using RPC gas estimates plus 20% per transaction. The deployer claimed the faucet, funded market `0`, then bought ten YES shares. That market's deadline is **2026-10-28 17:01:12 UTC**. RPC URLs and private keys remain local/hosted secrets.

## On-Chain vs Off-Chain Boundary

On-chain responsibilities (M3 creation/trading deployed; resolution and payouts planned):

- Market state.
- Trades.
- LMSR pricing.
- YES/NO share ownership.
- Challenge state.
- Resolver registry.
- Resolver voting.
- Settlement.
- Payouts.

Off-chain responsibilities (indexer/API implemented; hosted integration and oracle work remain):

- Esports API calls.
- API credentials.
- Oracle automation.
- Backend API.
- Indexing.
- PostgreSQL derived views.
- Initial bootstrap workflows.

The project should not be described as fully trustless or fully permissionless.

## Planned Market Lifecycle

M3 currently creates markets directly in `OPEN`. Quotes and buys require `block.timestamp < tradingDeadline`, even if the stored state remains `OPEN`. The fuller lifecycle below is future design, not a set of implemented transitions; the current enum order remains the seven states in the approved M3 interface.

```text
CREATED
  -> OPEN
  -> CLOSED
  -> PROPOSED
  -> FINALIZED
  -> CLAIMABLE

Dispute path:

PROPOSED
  -> DISPUTED
  -> RESOLVER_VOTING
  -> FINALIZED
  -> CLAIMABLE
```

Possible exceptional states include `POSTPONED`, `VOID`, and `ORACLE_TIMEOUT`.

Important invariants:

- Trading at or after close time must fail.
- Challenged markets must not finalize through the normal unchallenged path.
- Duplicate payouts must fail.
- Unauthorized resolver voting must fail.
- Conflicted resolver participation must fail.

## Current And Planned Interfaces

| Boundary | Interface | Status |
|---|---|---|
| Frontend -> contract | `getMarket(0)` | M2 read implemented; M3 returns two additional quantity fields and needs new ABI/address |
| Contract -> indexer | normalized `MarketCreated` projection | canonical creation log decoded live; hosted database projection pending |
| Backend -> frontend/dev tools | `GET /health`, sample-match reads | implemented |
| Frontend -> contract | guarded quote/buy and position read | implemented in contract; frontend integration pending |
| Contract -> indexer | `TradeExecuted` with complete post-trade projection fields | confirmed live buy and decoding verified; hosted database projection pending |
| Backend -> frontend | indexed market, trade, transaction-hash lookup, and indexer-status reads | implemented; hosted API deployment and frontend integration pending |

See `interfaces/M3_TRADING_INTERFACE.md` for the approved trading-interface freeze and `milestones/MILESTONE_3.md` for the recovery model and acceptance criteria.

## Setup Notes

Current frontend commands:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

Backend commands:

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m scripts.seed_sample_matches
uvicorn app.main:app --reload
```

Set `DATABASE_URL` in `backend/.env` to the Supabase PostgreSQL connection string before seeding/running.

Contract setup and deployment commands are documented in `contracts/README.md`. Database migrations use `alembic upgrade head`. The indexer supports one-shot synchronization with `python -m app.indexer.worker --once`, continuous polling without a flag, and deterministic projection rebuilding with `--rebuild`; hosted setup is documented in `DEPLOYMENT_RUNBOOK.md`.

## Known Gaps

- The frontend still uses the M2 address/ABI; switch both to the published M3 deployment when integrating trading.
- Deployed `getMarket` returns six fields, with market ID supplied by the lookup/event rather than returned. The handoff validator accepts this ABI; the identifier representation remains a consumer-review follow-up.
- No contract write or trading interface exists in the frontend.
- The public manifest, ABIs, and confirmed events are available. Hosted worker/database/API verification and the full frontend demo remain pending.
- Resolver randomness, address-level conflicts, quorum, snapshot, retry, and timeout/liveness behavior are proposed for Milestone 4; team approval, contracts, and the ABI remain outstanding.
- Backend sample-match data is fake/off-chain and exists only for Milestone 2 fallback display.
