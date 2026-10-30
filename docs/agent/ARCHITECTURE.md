# AC_ON Architecture

AC_ON is a testnet-only decentralized esports prediction market. Users connect an Ethereum wallet and trade YES/NO shares on binary esports match outcomes. The planned product is not fully trustless or fully permissionless: contract state should be authoritative for markets and payouts, while esports APIs, oracle automation, initial resolver bootstrapping, and indexing are trusted/off-chain support systems.

This document describes the repository as currently inspected. Do not treat planned components as implemented.

## Current Repo State

| Area | Status | Notes |
|---|---|---|
| Frontend | implemented; locally integrated | React + Vite + TypeScript app under `frontend/` supports M3 quotes, guarded buys, positions, indexed trades, and submitted/mined/indexed progress. |
| Wallet | implemented | Coinbase Smart Wallet and injected-wallet connectors through wagmi. Use MetaMask for Ethereum Sepolia writes because Coinbase Smart Wallet does not support sending transactions on that network; the local Anvil demo uses the development wallet. |
| Chain config | implemented | Environment-driven configuration supports local Anvil and the deployed Ethereum Sepolia M3 token/market pair (chain ID `11155111`) with the published six-output ABI. |
| Contracts | deployed and smoke-tested | ACON-funded creation, LMSR quotes, guarded buys, positions, and `TradeExecuted` are deployed from `6e30d51`. Market `0` and a ten-share YES buy are confirmed. |
| Backend | implemented; locally integrated | FastAPI app has health, deprecated sample-match endpoints, and paginated indexed market/trade/status reads. The local frontend/indexer/API path is verified; hosted acceptance remains. |
| Oracle | planned | No oracle service found. |
| Indexer | implemented; locally integrated | Confirmed projections, checkpoints, rebuild/reorg recovery, RPC polling, and ABI decoding exist. Canonical Sepolia event decoding and the complete local projection/API flow passed; hosted persistent indexing/API verification remains. |
| Database | Sepolia projections locally verified | Supabase revision `20261018_0001` is applied. A local worker populated one Sepolia market and two trades on 2026-10-22; the local API smoke check passed. Persistent hosted worker/API operation remains pending. |
| CI | implemented | GitHub Actions runs frontend build, backend tests, and contract formatting/build/tests. |

## Current Diagram

```text
Verified local M3 end-to-end path:
User Browser -> React / wagmi / viem -> local wallet -> ACON approval + guarded buy
     ^                                                        |
     |                                                        v
indexed state <- FastAPI <- derived SQLite <- indexer <- confirmed Anvil logs

Verified Sepolia contract path:
Funded EOA / MetaMask -> ACON approval -> guarded buy -> confirmed TradeExecuted
                                                        |
                                                        v
                           local worker -> Supabase -> local FastAPI smoke check

Remaining hosted acceptance path:
Sepolia logs -> hosted worker -> PostgreSQL -> hosted FastAPI -> deployed frontend

Future scope: oracle proposals, challenges, resolver voting, settlement, payouts.

Authoritative state: blockchain contracts
Derived state: PostgreSQL
```

## Frontend

Status: M3 trading interface implemented and locally integrated.

The frontend lives in `frontend/` and uses React, Vite, TypeScript, Tailwind, wagmi, viem, and Coinbase Wallet SDK. It supports wallet connection, network/configuration checks, ACON faucet and balance reads, market reads, LMSR quotes, user-selected slippage converted to `maxCost`, guarded buys, authoritative position reads, recent indexed trades, and explicit submitted/mined/indexed states.

PR #20 replaced the M2 placeholder contract with environment-driven M3 addresses and the published six-output ABI. A fresh local Anvil run verified the entire UI path through the indexer and API. Ethereum Sepolia reads work with the configured deployment, but writes require an injected wallet such as MetaMask because Coinbase Smart Wallet currently reports Sepolia as unsupported. Hosted API/indexer acceptance remains pending.

## Contracts

Status: deployed M3 guarded-buy implementation; live contract smoke test passed.

`ACONTestToken` is an 18-decimal test ERC-20. Each address can call its permissionless `faucet()` once for 1,000 ACON. The immutable `paymentToken` in `PredictionMarket` is set at construction. Creation and buys pull ACON from `msg.sender` using the caller's token allowance; positions are also credited only to that caller. No native ETH is accepted by these operations.

Creation atomically collects the exact LMSR subsidy, allocates a sequential market ID, and initializes `OPEN` with zero quantities. Both `quoteBuy` and `buy` call `LMSR.buyCost`. Execution enforces `actualCost <= maxCost`, collects the actual payment, updates the caller's shares plus market quantities/collateral, and emits the frozen event. Both mutators hold a shared reentrancy guard across the token call. The constructor rejects a zero token address but relies on deployment to supply the intended ACON token.

The implementation's 39 Foundry tests pass, including the pure-math fuzz/invariant suite. Runtime bytecode matches the deployed build, and a live ten-share YES buy passed exact payment/position/event checks after two confirmations. The [contracts README](../../contracts/README.md) gives the deployed six-output `getMarket` ABI, revert behavior, commands, and coverage follow-ups. Local frontend/indexer/database/API integration is verified; hosted Sepolia application acceptance remains. Sells, resolution, settlement, and payouts are deferred.

The implementation follows the approved M3 trading boundary: custom 18-decimal `ACON` test ERC-20, internal pure `LMSR.sol`, creator-funded subsidy, guarded buys with `maxCost`, and deterministic post-trade `TradeExecuted` values. See [`interfaces/M3_TRADING_INTERFACE.md`](interfaces/M3_TRADING_INTERFACE.md) for the frozen parameters and ABI contract.

## Backend

Status: indexed APIs implemented; hosted M3 acceptance pending.

The FastAPI service runs from `backend/` and exposes indexed markets, trades, transaction-hash lookup, and indexer status with freshness metadata. Health/sample-match endpoints remain from M2. It connects through `DATABASE_URL`; the local Anvil browser flow passed, and a local Sepolia worker/API backed by Supabase passed the read-only smoke check. Hosted worker/API and deployed-frontend validation remain pending.

The sample matches are fake display data only. They are not on-chain markets and must not be treated as authoritative market state.

## Milestone 4 Target Design

Status: [target design approved and merged in PR #28](interfaces/M4_FEATURE_COMPLETE_INTERFACE.md); no fixture registration, sell, proposal, challenge, resolver, settlement, or claim code is deployed. The [M4 owner/test plan](milestones/MILESTONE_4.md) requires local feature completeness and a fresh Sepolia contract smoke test; public Vercel/Render/Supabase integration is a stretch target and remains an M5 deliverable if unfinished.

The fixture flow is deterministic mock or manual JSON fixture/result import with organizer evidence → restricted on-chain registration of selected fixture IDs and Team A/YES, Team B/NO → one user-funded market per registered fixture. The key is `keccak256(abi.encode(providerId, gameId, externalMatchId))`. A PandaScore adapter is optional only with written permission for this use; no paid plan is required. Importing a listing does not create a market. The contract checks its registry, so the registrar/source remain trusted inputs. The backend and PostgreSQL remain derived; users submit trades, challenges, resolver votes, and claims through wallets.

The M4 design adds guarded LMSR sells rounded down with `minReturn`, 1 ACON per winning share, 0.5 ACON per outstanding share on VOID, separate 10 ACON challenge-bond accounting, and creator surplus only above claim reserves after settlement. Matthew must prove fixed-point solvency before payout code merges. A proposal is immutable and has a 24-hour challenge window. After exact events/reads freeze, the indexer/API will project sells, proposals, challenges, committees/votes, outcomes, and claims; contract reads remain authoritative for spendable and claimable amounts.

## Oracle

Status: planned.

No oracle service exists yet. M4 requires deterministic mock and manual JSON adapters with organizer evidence URL/hash; PandaScore is optional only after written permission. Result parsing is separate from a least-privilege on-chain proposer. Proposals are immutable; corrections use challenges. A proposer cannot settle a challenged market. Seven days without a proposal after the trading deadline enables anyone to start resolver selection.

## Resolver Protocol

Status: target design approved in merged PR #28; not implemented. Exact ABI types still need a freeze.

Resolution remains authoritative on-chain. A 2-of-3 Sepolia Safe controlled by Benny, Matthew, and Adriel owns the allowlist, role recovery, and VRF subscription. Registry changes apply to future selections; removal does not rewrite an active round. PostgreSQL may project registry, selection, votes, deadlines, and outcomes, but never selects resolvers or decides outcomes.

A challenged result or seven days without any proposal opens round 1. Round 1 without quorum opens exactly one replacement round. Each selection round stores a fixed seven-day deadline and eligible-candidate snapshot; a retry after 30 minutes reuses both. Exclusions cover creator, fixture registrar, proposer, challenger, trader, position holder, resolver-admin address, and committee duplicates. Checks are address-level only. At least ten resolver-only testnet addresses are recommended; four humans control them, so this is address-level separation.

Chainlink VRF v2.5 on Sepolia selects five distinct addresses using one random word, three block confirmations, and test LINK billing. The contract tracks one current request ID per market/round. Superseded, duplicate, mismatched, or late callbacks emit `VRFFulfillmentIgnored` without state change. If no valid committee exists by the fixed deadline, anyone may trigger `VOID`.

Each selected resolver casts one direct YES, NO, or VOID vote during a 48-hour period. Three matching YES or NO votes finalize the winner; three VOID votes make the market VOID. Round 2 takes a new snapshot and excludes round-1 resolvers if five alternatives exist; otherwise still-eligible round-1 addresses may be reused. No round-2 quorum leads to VOID. Both terminal states expose claims.

Direct voting authorizes `msg.sender`; relayed voting and EIP-1271 are outside M4. Exact Solidity types/indexed event fields and Matthew's collateral proof still gate dependent implementation. The approved event/read categories are in the [M4 design decision](interfaces/M4_FEATURE_COMPLETE_INTERFACE.md).

## Indexer

Status: worker implemented and locally integrated; live Sepolia RPC/ABI decoding verified; hosted indexing pending.

The backend contains a provider-independent event indexer with normalized `MarketCreated` and approved `TradeExecuted` handlers. It persists a unique `(chain_id, transaction_hash, log_index)` event identity, checks range-end hashes before and after applying each batch, advances each bounded block range atomically with its checkpoint, waits for configurable confirmations, and rebuilds derived projections when the checkpoint block hash no longer matches the canonical chain. PR #15 added JSON-RPC retrieval/polling and the strict ABI decoder; PRs #17 and #18 added transaction lookup, freshness/replay checks, versioned handoff validation, and a read-only smoke command. The published manifest passes validation, local Anvil logs reached the UI through FastAPI, and real Sepolia logs reached Supabase and passed the local API smoke check. Persistent hosted worker/API operation remains to be verified.

## Database

Status: Supabase schema applied and Sepolia projections verified through a local worker/API; hosted service operation unverified.

Milestone 2 uses Supabase PostgreSQL as a hosted development database so teammates do not need local PostgreSQL. PostgreSQL should be treated as derived/indexed or demo display state. Blockchain state is authoritative.

## Deployment Status

Status: contracts live; local application integration verified; hosted application integration pending.

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

M3 creates markets directly in `OPEN` and checks the deadline without changing stored state. The decided M4 lifecycle below is **not implemented**; the current M3 enum remains the deployed interface. M4 stores only `OPEN`, `CLOSED`, `PROPOSED`, `DISPUTED`, `RESOLVER_SELECTION`, `RESOLVER_VOTING`, `FINALIZED`, and `VOID`, in that order. Resolver round 1/2 is stored separately. `CLAIMABLE` is a derived read, never a state. The [target diagram](../architecture-preview.md#market-state-machine) uses the same transitions.

```text
REGISTERED FIXTURE -> one user-funded OPEN market -> CLOSED at deadline or evidenced early close
  -> PROPOSED (immutable YES/NO/VOID and evidence; 24-hour challenge window)
      -> no challenge -> FINALIZED (YES/NO) or VOID -> corresponding claims
      -> first challenge + 10 ACON bond -> DISPUTED -> RESOLVER_SELECTION (round 1)
  -> no proposal seven days after trading deadline -> RESOLVER_SELECTION (round 1)

RESOLVER_SELECTION (round 1 or 2; fixed seven-day deadline)
  -> current VRF request selects five -> RESOLVER_VOTING (48 hours)
  -> no valid committee by deadline -> VOID -> claims
RESOLVER_VOTING
  -> three YES/NO votes -> FINALIZED -> winning claims
  -> three VOID votes -> VOID -> both-outcome claims
  -> round 1 no quorum -> RESOLVER_SELECTION (round 2, new snapshot/deadline)
  -> round 2 no quorum -> VOID -> both-outcome claims
```

Postponement is fixture metadata; it never reopens or extends trading. `ORACLE_TIMEOUT` and `POSTPONED` are not stored market states. Expiry transitions require a callable on-chain action; a wall-clock deadline alone does not mutate storage.

Important invariants:

- Trading at or after close time must fail.
- Challenged markets must not finalize through the normal unchallenged path.
- Duplicate payouts must fail.
- Unauthorized resolver voting must fail.
- Conflicted resolver participation must fail.

## Current And Planned Interfaces

| Boundary | Interface | Status |
|---|---|---|
| Frontend -> contract | `getMarket(0)` | M3 six-output ABI and environment-driven address implemented and locally verified |
| Contract -> indexer | normalized `MarketCreated` projection | projected on Anvil and from canonical Sepolia logs into Supabase by a local worker; hosted worker operation pending |
| Backend -> frontend/dev tools | `GET /health`, sample-match reads | implemented |
| Frontend -> contract | guarded quote/buy and position read | implemented and verified in the local browser flow; Sepolia writes require MetaMask |
| Contract -> indexer | `TradeExecuted` with complete post-trade projection fields | projected from confirmed Sepolia logs into Supabase by a local worker; hosted worker operation pending |
| Backend -> frontend | indexed market, trade, transaction-hash lookup, and indexer-status reads | implemented and locally verified; hosted API deployment remains pending |

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

- The public manifest, ABIs, and confirmed events are available. Hosted worker/database/API verification and the deployed-frontend Sepolia demo remain pending.
- Coinbase Smart Wallet connects and reads but cannot send Ethereum Sepolia transactions; use MetaMask for the hosted Sepolia demo. The local Anvil demo uses the development wallet.
- The reproducible local cross-layer flow has been manually verified, but it is not yet an automated end-to-end CI job.
- Local SQLite is suitable for the reproducible Anvil demo; PostgreSQL/Supabase preserves exact large-integer Sepolia projections and passed the local API smoke check.
- Resolver randomness, address-level conflicts, quorum, snapshot, retry, and timeout/liveness behavior are part of the PR #28-approved M4 design; contracts and exact ABI remain outstanding.
- Backend sample-match data is fake/off-chain and exists only for Milestone 2 fallback display.
