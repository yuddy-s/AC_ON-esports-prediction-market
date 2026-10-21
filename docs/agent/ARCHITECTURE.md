# AC_ON Architecture

AC_ON is a testnet-only decentralized esports prediction market. Users connect a Coinbase Wallet and trade YES/NO shares on binary esports match outcomes. The planned product is not fully trustless or fully permissionless: contract state should be authoritative for markets and payouts, while esports APIs, oracle automation, initial resolver bootstrapping, and indexing are trusted/off-chain support systems.

This document describes the repository as currently inspected. Do not treat planned components as implemented.

## Current Repo State

| Area | Status | Notes |
|---|---|---|
| Frontend | implemented | React + Vite + TypeScript app under `frontend/`. |
| Wallet | implemented | Coinbase Smart Wallet and injected wallet fallback through wagmi. |
| Chain config | implemented | Frontend and Milestone 2 deployment use Ethereum Sepolia (chain ID `11155111`), selected for Milestone 3. |
| Contracts | guarded-buy implementation | Commit `4c57dc0` on `feature/guarded-buy` integrates ACON-funded creation, LMSR quotes, guarded buys, positions, and `TradeExecuted`. Review, fresh Sepolia deployment, and live integration are pending. |
| Backend | foundation | FastAPI app has health, deprecated sample-match endpoints, and paginated indexed market/trade/status reads. |
| Oracle | planned | No oracle service found. |
| Indexer | foundation + RPC worker | Confirmed projections, checkpoints, rebuild/reorg recovery, RPC polling, and ABI decoding exist; live validation awaits the M3 deployment handoff. |
| Database | foundation | Alembic manages indexed contract/checkpoint/log/market/trade tables; sample data remains non-authoritative fallback data. |
| CI | scaffolded | GitHub Actions runs frontend build, backend tests, and contract formatting/build/tests. |

## Current Diagram

```text
Implemented:

User Browser
    |
    v
React + Vite frontend
    |
    v
wagmi + viem
    |
    +--> Coinbase Smart Wallet connector
    +--> Injected wallet connector
    |
    v
Ethereum Sepolia

Planned:

React frontend --> Ethereum Sepolia contracts --> contract events
        |                 ^                       |
        v                 |                       v
FastAPI backend ---- oracle service          indexer
        |                                         |
        v                                         v
PostgreSQL API/cache state                PostgreSQL indexed state

Authoritative state: blockchain contracts
Derived state: PostgreSQL
```

## Frontend

Status: implemented, minimal prototype.

The frontend lives in `frontend/` and uses React, Vite, TypeScript, Tailwind, wagmi, viem, and Coinbase Wallet SDK. It currently supports wallet connection and balance display.

The app reads placeholder market `0` from the earlier Ethereum Sepolia deployment. M3 quote/buy UI and indexed-state transitions remain pending frontend integration.

## Contracts

Status: M3 guarded-buy implementation, deployment pending.

`ACONTestToken` is an 18-decimal test ERC-20. Each address can call its permissionless `faucet()` once for 1,000 ACON. The immutable `paymentToken` in `PredictionMarket` is set at construction. Creation and buys pull ACON from `msg.sender` using the caller's token allowance; positions are also credited only to that caller. No native ETH is accepted by these operations.

Creation atomically collects the exact LMSR subsidy, allocates a sequential market ID, and initializes `OPEN` with zero quantities. Both `quoteBuy` and `buy` call `LMSR.buyCost`. Execution enforces `actualCost <= maxCost`, collects the actual payment, updates the caller's shares plus market quantities/collateral, and emits the frozen event. Both mutators hold a shared reentrancy guard across the token call. The constructor rejects a zero token address but relies on deployment to supply the intended ACON token.

The implementation's unit and existing pure-math fuzz/invariant tests pass locally. The [contracts README](../../contracts/README.md) gives the exact six-output `getMarket` ABI, revert behavior, commands, and remaining coverage follow-ups. This is not a completed live MVP: review, a fresh Ethereum Sepolia deployment, and frontend/indexer integration remain pending. Sells, resolution, settlement, and payouts are deferred.

The implementation follows the approved M3 trading boundary: custom 18-decimal `ACON` test ERC-20, internal pure `LMSR.sol`, creator-funded subsidy, guarded buys with `maxCost`, and deterministic post-trade `TradeExecuted` values. See [`interfaces/M3_TRADING_INTERFACE.md`](interfaces/M3_TRADING_INTERFACE.md) for the frozen parameters and ABI contract.

## Backend

Status: scaffolded.

The backend is a FastAPI service intended to run from `backend/`. For Milestone 2 it exposes health/sample-match API endpoints backed by Supabase PostgreSQL through `DATABASE_URL`.

The sample matches are fake display data only. They are not on-chain markets and must not be treated as authoritative market state.

## Oracle

Status: planned.

No oracle service exists yet. Intended behavior: compare approved esports API results, propose outcomes on-chain when rules allow, route disagreements or timeouts to dispute/manual paths, and avoid unilateral settlement of disputed markets.

## Indexer

Status: foundation.

The backend contains a provider-independent event indexer with normalized `MarketCreated` and approved `TradeExecuted` handlers. It persists a unique `(chain_id, transaction_hash, log_index)` event identity, checks range-end hashes before and after applying each batch, advances each bounded block range atomically with its checkpoint, waits for configurable confirmations, and rebuilds derived projections when the checkpoint block hash no longer matches the canonical chain. PR #15 added validated JSON-RPC retrieval, bounded retries and range splitting, continuous polling, and an ABI-driven decoder that fails closed unless both approved events are present. Live Sepolia validation still needs Benny's exact compiled ABI and deployment record.

## Database

Status: scaffolded.

Milestone 2 uses Supabase PostgreSQL as a hosted development database so teammates do not need local PostgreSQL. PostgreSQL should be treated as derived/indexed or demo display state. Blockchain state is authoritative.

## Deployment Assumptions

Status: partial.

Ethereum Sepolia is the selected Milestone 3 network. `contracts/script/Deploy.s.sol` now deploys ACON and PredictionMarket, claims the deployer's faucet, approves the exact subsidy, and seeds market #0 with a seven-day deadline. It has been simulated locally, but no fresh M3 Sepolia deployment is recorded. The handoff must include both addresses, deployment transaction/block, exact-build ABI/source revision, demo market ID, and the two-confirmation indexer default. RPC URLs and private keys remain local/hosted secrets and must not be exposed to the frontend or committed.

## On-Chain vs Off-Chain Boundary

On-chain planned responsibilities:

- Market state.
- Trades.
- LMSR pricing.
- YES/NO share ownership.
- Challenge state.
- Resolver registry.
- Resolver voting.
- Settlement.
- Payouts.

Off-chain planned responsibilities:

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
| Contract -> indexer | normalized `MarketCreated` projection | foundation and RPC/ABI worker merged; new deployment handoff pending |
| Backend -> frontend/dev tools | `GET /health`, sample-match reads | implemented |
| Frontend -> contract | guarded quote/buy and position read | implemented in contract; frontend integration pending |
| Contract -> indexer | `TradeExecuted` with complete post-trade projection fields | implemented in contract; live event decoding/projection validation pending |
| Backend -> frontend | indexed market, trade, and indexer-status reads | foundation implemented |

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

- The checked-in contract and the existing Sepolia deployment came from different source versions.
- `getMarket` returns six fields, with market ID supplied by the lookup/event rather than returned; confirm that representation with consumers before the ABI handoff.
- No contract write or trading interface exists in the frontend.
- The RPC/ABI worker is implemented but cannot be validated against live contract logs until the final ABI, address, and deployment block are published.
- Resolver selection randomness, conflict exclusions, and timeout/liveness behavior are not decided.
- Backend sample-match data is fake/off-chain and exists only for Milestone 2 fallback display.
