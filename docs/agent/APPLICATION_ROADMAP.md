# AC_ON Application Roadmap

This is the canonical implementation checklist for coding agents and team members. It records what exists, what remains, who owns each area, and whether work can proceed without another team decision. Detailed milestone scope remains in `milestones/` and current assignments remain in `TASKS.md`.

Last reviewed: 2026-10-29 after PR #28 approval and merge. Current implementation evidence below remains the M3 baseline; M4 work is not yet implemented.

PRs #10, #12-#20, and #22-#26 are merged into `dev`; PR #27 promoted the M3 snapshot to `main`. This includes the database/indexer/API foundation, approved M3 trading interface, bounded LMSR library, RPC/ABI worker, ACON token, guarded-buy market integration, transaction lookup, versioned deployment handoff, M3 frontend, and proposed Milestone 4 resolver decision record. ACON and PredictionMarket were deployed from `6e30d516669e51d7f3e4bff0d8670168da9b1f83`; market `0` and a ten-share YES buy are confirmed on Sepolia. The complete guarded-buy path was verified locally from a fresh browser through Anvil, the indexer, FastAPI, and back to the UI. Separately, a local Sepolia worker populated Supabase and passed the local API smoke check. Hosted worker/API/frontend acceptance remains pending.

The canonical M3 integration input is [`deployments/sepolia-m3.json`](../../deployments/sepolia-m3.json). The [deployment and trade record](../../contracts/deployments/sepolia-m3-2026-10-21/README.md) includes the exact-build ABIs, receipts, balance checks, and gas-estimation recovery. Market `0` stopped accepting buys on **2026-10-28 at 17:01:12 UTC**; use a new funded market for any later M3 trade demo. The M4 target needs its own deployment and manifest.

## Status Key

- **Done**: implemented in the repository. A feature-branch item is not integrated until its pull request merges.
- **Ready**: can be implemented now with repository information already available.
- **Partial**: useful generic work can proceed, but final integration needs the listed handoff.
- **Pending**: implementation/preparation exists, but execution or verification has not happened yet.
- **Blocked**: implementation would guess an authoritative interface, secret, deployment, or protocol decision.
- **Deferred**: intentionally outside the milestone named in the task, unless the team changes scope.

## Active Milestone 4 Target Design

The PR #28-approved decision set makes full public Vercel/Render/Supabase/Sepolia integration an **M4 stretch target**, not an M4 acceptance gate. M4 requires complete implemented features and normal/disputed/timeout/VOID/claim local Anvil flows, component tests, full test plan, final ABI/docs alignment, and fresh Sepolia contracts with focused transaction smoke. The [M4 milestone](milestones/MILESTONE_4.md) owns assignments and tests; [the M4 design decision](interfaces/M4_FEATURE_COMPLETE_INTERFACE.md) owns target protocol rules. The [active queue](TASKS.md#active-milestone-4-feature-complete-queue) assigns dependent PRs. Exact ABI argument types/indexed fields remain to be frozen before code merges.

Dependency order: build the required deterministic mock and manual JSON adapters with organizer evidence; enable optional PandaScore only after written use permission, without a paid plan; freeze exact ABI and Matthew's collateral proof; set up a 2-of-3 Safe, narrow registrar/proposer keys, VRF subscription, and at least ten resolver-only testnet addresses; implement contracts, oracle/indexer/API, and frontend; integrate on Anvil and smoke-test new Sepolia contracts. The backend imports fixtures but does not create user markets. The restricted registrar registers selected fixtures, one market per fixture, and users create markets. The contract cannot query the backend or verify source truth.

Full public integration may finish in M4 as a stretch result; otherwise M5 completes it. This does not convert unimplemented sells, oracle proposals, resolver voting, settlement, VOID, or claims into completed features. Every implementation PR updates its affected README, interface/API/deployment handoff, tests, and recovery docs. Preserve the approved M3 trading record.

## What An ABI Is

An Ethereum Application Binary Interface, or **ABI**, is a JSON description of a smart contract's public functions, errors, and events. It tells the frontend and backend:

- which contract functions exist and which arguments and return types they use;
- how to encode a function call such as `buy(marketId, outcome, shares, maxCost)`;
- how to decode returned bytes, revert errors, and event logs;
- which event topic and data fields correspond to `MarketCreated` or `TradeExecuted`.

The Solidity source is written for people and the compiler. The ABI is the machine-readable contract shared by Solidity, the frontend, and the indexer. If an event field or type changes, its event signature changes, so all consumers must update together. Benny owns the Solidity implementation and deployment, while the team jointly freezes the ABI because every subsystem consumes it.

## Current Repository Baseline

| Area | Current state | Integration status |
|---|---|---|
| Frontend | M3 wallet/config checks, ACON faucet/balance, market/position reads, LMSR quote, guarded buy with slippage, recent indexed trades, and submitted/mined/indexed states. | Merged in PR #20 and verified in the local Anvil cross-layer flow; hosted Sepolia acceptance remains. |
| Contracts | ACON faucet/token, atomic creator subsidy, LMSR quotes, guarded buys, share balances, and complete trade events. | Deployed from PR #16 merge commit `6e30d51`; seeded market and live guarded buy verified. Sells/resolution/payouts remain deferred. |
| Backend API | Health, deprecated sample data, and indexed market/trade/status endpoints. | Local FastAPI returned the confirmed Sepolia market/trade from Supabase and passed the read-only smoke check; hosted API deployment remains. |
| Database | Alembic models for indexed contracts, checkpoints, processed logs, markets, and trades. | Revision `20261018_0001` is applied to Supabase; a local worker populated one Sepolia market and two trades on 2026-10-22. |
| Indexer | Confirmed-log projections, atomic checkpoints, idempotency, restart/reorg recovery, JSON-RPC transport, polling worker, and strict ABI decoder. | Local Sepolia worker and API smoke check passed against Supabase; persistent hosted worker operation remains pending. |
| Oracle | Design boundary only. | Not implemented. |
| Resolver | Design and ownership boundary only. | Not implemented; Milestone 4 scope. |
| CI | Frontend tests/build, backend migrations/tests, and Foundry format/build/tests. | Implemented and passing on the current baseline; the README supplies the reproducible local cross-layer equivalent, but no automated end-to-end job exists. |

## Pull Request Integration Review

### PR #10: backend indexer foundation

- Contains the database/indexer/API foundation described in this roadmap.
- The branch was refreshed after PRs #12 and #13 and merged into `dev`.
- The four review findings were resolved: mid-batch reorganization consistency, direct-to-`OPEN` projection, the two-confirmation default, and an explicit derived-state marker on trade responses.

### PR #12: Milestone 3 trading-interface decision

- Approved an 18-decimal mintable `ACON` test ERC-20 as collateral; Sepolia ETH is gas only.
- Froze the outcome order as `YES = 0`, `NO = 1` and retained the existing market-state numeric order.
- Approved creation directly into `OPEN`, atomic creator-subsidy collection, guarded `buy(..., maxCost)`, and the `MarketCreated`/`TradeExecuted` events anticipated by the indexer foundation.
- Approved maximum quantity `2_000e18`, maximum trade `100e18`, no fees, and a two-confirmation Sepolia default.
- Correctly keeps sells, settlement, payouts, complete VOID behavior, oracle execution, and resolver execution outside M3.
- PR #12 is approved and merged; its decision record is the cross-layer baseline.

Resolved backend reconciliation:

- PR #12 was authored against `dev` before PR #10, so its `TASKS.md` backend statuses describe the older scaffold. When PR #10 is refreshed after PRs #12 and #13, retain PR #10's implemented foundation statuses.
- The indexer projects a state-less `MarketCreated` event as `OPEN`.
- Backend configuration defaults to two confirmations and remains configurable.
- The approved decision record states that clients treat an `OPEN` market at or after its deadline as not tradable; an explicit close transition is deferred.
- Commit 4c57dc0 implements a permissionless, one-time-per-address faucet for 1,000 ACON on the test token. Demo wallets approve the market to spend ACON; see the contract README for the deployment and buyer procedure.

### PR #13: bounded LMSR library

- Implements stable log-sum-exp pricing with 1e18 precision and `B = 50e18`.
- Pins PRBMath v4.2.2 by Git submodule commit and updates CI to initialize submodules.
- Implements the approved subsidy constant, quantity/trade bounds, deterministic vectors, fuzz tests, and stateful bounded-loss/telescoping invariants.
- Leaves token movement and `PredictionMarket` integration to Benny, which preserves the documented ownership boundary.
- All configured checks pass. No blocking math or dependency issue was identified during this review.
- PR #13 is approved and merged into `dev`.

Verification confirmed that the Foundry invariant executed 256 runs and 128,000 calls with zero reverts. The refreshed branch preserved both the approved interface decision link and the implemented LMSR/submodule instructions.

### Recommended merge order

1. **Done:** approve and merge PR #12 so its product and interface decisions become the integration baseline.
2. **Done:** refresh PR #13 from the new `dev`, preserve both documentation sets, rerun CI with submodules, and merge it.
3. **Done:** refresh PR #10 from the new `dev`, retain its implemented backend statuses, fix all four review findings, rerun CI, and merge it.
4. **Done:** Yudhveer's RPC/ABI worker was merged in PR #15.
5. **Done:** Benny's ACON/LMSR integration merged in PR #16; both contracts are deployed and the exact-build handoff is published in PR #19 for consumer review.
6. **Done:** PRs #17 and #18 merged transaction lookup, freshness/replay checks, the versioned handoff validator, and the read-only live smoke command.
7. **Done:** PR #19 published the validated Sepolia deployment manifest, exact-build ABIs, and guarded-buy evidence.
8. **Done:** PR #20 integrated the M3 frontend and its quote/buy, position, indexed-data, and submitted/mined/indexed flows.
9. **Done:** PR #22 merged an earlier resolver proposal; approved and merged PR #28 contains the M4 decision set. Freeze exact ABI types before dependent code merges.

### PR #16 source-interface consumer check

The merged Solidity `MarketCreated` and `TradeExecuted` declarations match the backend decoder's required field names, types, order, and indexed positions. Exact compiler-generated ABIs are in `deployments/abi/`, and the [live trade fixture](../../contracts/deployments/sepolia-m3-2026-10-21/guarded-buy.json) records the canonical log. Both creation and trade were fetched and decoded with the backend's real RPC client and ABI decoder. PR #20 updated the frontend to the M3 addresses and six-output `getMarket` ABI. The deployed contract returns question, deadline, state, creator, YES quantity, and NO quantity; the market ID comes from the call argument or event rather than a return value. The frontend and handoff validator both consume this representation.

The indexer status API reports block lag against its last observed head and exposes `updated_at` for detecting a stopped worker. Frontend freshness work must consider both: a stopped worker with a once-current checkpoint can still report zero lag. PR #17 merged into `dev` with full-replay equality coverage, database-outage responses, transaction lookup, and stale status timestamp checks. PR #18 merged the versioned deployment handoff and live smoke check. The populated manifest passes validation; running the hosted smoke check now requires the configured API/worker and API URL.

### Frontend backend-API handoff

After a wallet buy is mined successfully, use `GET /api/trades/by-transaction/{transaction_hash}` to check for its confirmed `TradeExecuted` projection. The path requires a `0x`-prefixed 32-byte hash; hex case is accepted and the response hash is lowercase. The response contains `transaction_hash` and an `items` array of trade objects, ordered by block and log index. An empty array with HTTP 200 means no matching trade is indexed yet; it does not prove the wallet transaction failed. Invalid hashes return HTTP 422. Database read failures return a server error, not an empty array.

Read `/api/indexer/status` alongside the lookup. Its `updated_at` is a UTC ISO 8601 timestamp for the checkpoint's last update, or `null` before the worker observes a head; successful head observations refresh it. Confirm `configured`, chain ID, and contract address match the wallet's deployed market. While waiting, check that the update is recent and `last_safe_block` has reached the mined receipt's block. The default two-confirmation worker normally has nonzero `lag_blocks`; a zero value alone does not establish freshness. If the safe checkpoint has passed the receipt block and the lookup is still empty, inspect the receipt and its logs for `TradeExecuted` or a deployment mismatch. The backend never submits buys. See [backend/README.md](../../backend/README.md#frontend-indexing-synchronization) for the endpoint details.

## Milestone 3 Definition Of Done

The implementation-complete M3 slice is the path below. It has been verified locally on Anvil. A stricter public-deployment acceptance claim requires rerunning the same path with the hosted Sepolia worker, PostgreSQL/API services, and deployed frontend:

```text
wallet requests quote
  -> wallet submits guarded LMSR YES/NO buy
  -> transaction is mined and emits TradeExecuted
  -> indexer reads and decodes the confirmed log exactly once
  -> PostgreSQL stores the derived market and trade state
  -> FastAPI returns the indexed state
  -> frontend separately shows submitted, mined, and indexed states
```

The full resolver committee, production esports provider, selling, settlement, payouts, and advanced portfolio UI are not required for this M3 path.

## Immediate Milestone 3 Checklist

| Order | Owner | Work | Status | Dependency or acceptance condition |
|---:|---|---|---|---|
| 1 | Team, coordinated by Yudhveer | Review and merge PR #12 to freeze the M3 cross-layer interface. | Done | Approved and merged. |
| 2 | Matthew | Refresh, review, and merge PR #13 implementing binary LMSR math. | Done | Approved, verified, and merged. |
| 3 | Yudhveer/team | Refresh and repair PR #10, then merge the indexer foundation into `dev`. | Done | Merged and included in the PR #14 integration baseline. |
| 4 | Benny | Integrate market creation, creator subsidy, quote, guarded buy, balances, and complete events. | Done | Merged in PR #16; live buy and ABI handoff verified. Additional security coverage remains. |
| 5 | Yudhveer | Implement JSON-RPC transport, polling worker, backfill, retries, range splitting, and operational logging. | Done | Merged in PR #15; hosted worker operation remains to be verified. |
| 6 | Yudhveer | Validate the ABI decoder and live market/trade projections. | Partial | Sepolia RPC retrieval/decoding and local worker/Supabase/API reconciliation passed; hosted worker/API operation remains. |
| 7 | Benny | Deploy the integrated contract to Sepolia and publish its handoff record. | Done | Deployed from `6e30d51`, seeded market `0`, verified a guarded buy, and published the manifest/ABIs/evidence in PR #19. |
| 8 | Yudhveer | Apply migrations and deploy API/worker using Render and Supabase. | Partial | Migration reported applied; the validated handoff is available. Configure hosted processes and verify live indexed data. |
| 9 | Adriel | Implement quote/buy UI and submitted/mined/indexed states. | Done | Merged in PR #20; M3 ABI/config, guarded buy, positions, API freshness, and transaction stages verified locally. |
| 10 | Team | Run and document the end-to-end buy demonstration. | Partial | Fresh local browser-to-contract-to-indexer-to-API-to-UI run passed; hosted Sepolia acceptance remains. |
| 11 | Team | Update design documentation, test plan/results, and presentation. | Partial | Canonical repo documentation is being reconciled; presentation claims must preserve the local-versus-hosted distinction. |

## Yudhveer Backend And Database Queue

### Ready now

- [x] Refresh and merge the repaired indexer foundation after PRs #12 and #13.
- [x] Review and coordinate PR #12's ABI/event freeze using the handoff checklist below.
- [x] Add a JSON-RPC client that calls `eth_blockNumber`, `eth_getBlockByNumber`, and `eth_getLogs`.
- [x] Validate hexadecimal RPC responses, contract addresses, block numbers, block hashes, transaction hashes, and log indexes.
- [x] Add bounded retries with backoff for temporary HTTP/RPC failures; do not retry invalid requests forever.
- [x] Split a requested block range when the provider rejects a range as too large.
- [x] Add a worker entry point for one-shot backfill and continuous polling with clean shutdown.
- [x] Add operational logs for completed sync state, RPC retries/range splits, rebuilds, and failures.
- [x] Test transient/non-retryable HTTP failures, malformed responses, oversized ranges, worker modes, and shutdown using mocked dependencies.
- [x] Add a deployment runbook for Alembic, Render API/worker processes, Supabase, secrets, health checks, rollback, and rebuild.
- [x] Add the ABI-version convention and manifest validator; the populated Sepolia manifest and exact-build ABIs are available in PR #19.
- [x] Confirm pagination limits, validation, empty responses, metadata, and lag reporting on the indexed APIs with local tests.

### Prepared for hosted integration

- [x] Build ABI-driven decoder dispatch that maps known event topics to normalized `ChainLog` values and rejects ABIs missing the approved events.
- [x] Prepare hand-built decoder fixtures; the published handoff now also contains the exact compiled ABI and raw confirmed `TradeExecuted` log.
- [x] Prepare the Alembic migration and read-only staging verification queries; revision `20261018_0001` was applied to the configured Supabase database on 2026-10-21 after backing up its three sample rows.
- [x] Prepare Render service/worker settings in the deployment runbook; the deployment record is supplied, while hosted execution requires the appropriate access and environment values.
- [x] Prepare a read-only Sepolia creation/trade-to-API smoke test; the manifest supplies its chain inputs, and execution awaits the configured live API/worker.
- [x] Coordinate Adriel's API client against the existing OpenAPI endpoints; local UI/API verification passed, while hosted Sepolia data remains pending.

### Provided and remaining inputs

- [x] Compiled ABIs from deployed source `6e30d516669e51d7f3e4bff0d8670168da9b1f83`, with validated versioned filenames and hashes.
- [x] Final Sepolia token/market addresses, deployment transactions/blocks, and successful creation/trade examples in `deployments/sepolia-m3.json`.
- [x] Contract behavior documented for creation subsidy, guarded buy, deadline, enum-decoder rejection, balance/allowance, and slippage reverts; consumer review remains.
- [x] ACON faucet/approval procedure documented and exercised by the deployer; additional frontend demo wallets need their own gas and faucet claim.
- [x] Supabase migration access was authorized for this session and the configured database migration was applied.
- [ ] Render access and the required RPC/database environment values for hosted deployment.

### Yudhveer M3 completion criteria

- [x] A new deployment can be registered by chain ID, address, deployment block, and ABI version.
- [x] Backfill begins at the configured deployment block and resumes from its database checkpoint.
- [x] Confirmed `MarketCreated` and `TradeExecuted` logs decode and project exactly once in automated/local validation.
- [x] Database and checkpoint changes for a block batch commit atomically.
- [x] Duplicate delivery, process restart, missed ranges, RPC failure, and a simulated reorganization pass automated tests.
- [x] `/api/indexer/status` reports observed head, safe checkpoint, lag, and freshness metadata.
- [x] Market and trade endpoints return paginated derived data with source-chain metadata.
- [ ] Supabase can be rebuilt deterministically from canonical contract events.
- [x] No wallet key, RPC credential, or database credential is stored in Git or returned through the API.

## Contract And ABI Handoff Checklist

Yudhveer may propose event fields because the indexer consumes them. Benny generates the final ABI, Matthew validates LMSR quantities and units, and Adriel validates frontend needs. The following handoff data is recorded in the [manifest](../../deployments/sepolia-m3.json), versioned ABIs, and [deployment/trade evidence](../../contracts/deployments/sepolia-m3-2026-10-21/README.md); consumer review and hosted acceptance remain separate tasks:

- [x] Git commit of the deployed contract source.
- [x] Chain ID (`11155111` for Sepolia).
- [x] Checksummed contract addresses.
- [x] Deployment transaction hashes and deployment blocks.
- [x] Generated JSON ABIs from that exact build.
- [x] Versioned ABI filenames supplied for indexer configuration.
- [x] Function inputs, outputs, custom errors, and access restrictions.
- [x] Event names, indexed parameters, non-indexed parameters, and exact Solidity types.
- [x] Market-state and outcome-enum numeric order.
- [x] Units: token/share base units (`1e18`), unscaled IDs, and Unix-second deadlines.
- [x] ACON address and 18 decimals; native Sepolia ETH pays gas only.
- [x] Successful creation and trade hashes, with the raw trade log and before/after checks.

Approved M3 event interfaces are:

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

These declarations match the approved PR #12 decision record and were deployed from merge commit `6e30d51`. All share, cost, and LMSR quantity fields use 1e18 base units. The decoder projects a newly created market as `OPEN` and fails startup if the supplied ABI does not contain these exact event shapes. The published ABI and canonical live creation/trade logs passed decoder validation and local worker/Supabase/API reconciliation; hosted worker/API checks remain.

The implemented `getMarket` returns six fields, with the market ID supplied by its argument/event rather than included in the return tuple. The frontend and backend handoff validator consume this representation. Exact signatures, units, errors, and current test coverage are in [`../../contracts/README.md`](../../contracts/README.md).

## Remaining Application Work By Owner

### Adriel: frontend and Web3

- [ ] Add broader indexed-market browsing; the M3 page currently shows the configured market, recent indexed trades, and explicit indexer freshness.
- [ ] Add wallet-based market creation using the deployed subsidy-funded contract interface (optional for the core buy demo).
- [x] Request an on-chain LMSR quote and submit a guarded buy with `maxCost`.
- [x] Display wallet rejection, submitted, mined, reverted, awaiting-indexer, and indexed states.
- [x] Display YES/NO positions using authoritative contract reads where appropriate.
- [ ] Add market status, challenge, resolver vote, claim, and portfolio flows in M4.
- [x] Add component tests and a documented reproducible local wallet/contract/API test path; automate the cross-layer path later.
- [ ] Configure Vercel without exposing server-only secrets.

### Benny: lifecycle and resolver contracts

- [x] Publish the exact-build ABI handoff with a validated manifest and live transaction evidence (PR #19).
- [ ] Complete consumer review of the deployed six-output `getMarket` ABI and identifier representation.
- [x] Implement market creation, subsidy enforcement, deadline/state rules, quote integration, guarded buy, balances, and events (merged in PR #16).
- [x] Use caller-only token payments/positions, balance/allowance checks, custom errors, and a shared reentrancy guard across token transfers. State updates follow successful transfers under the guard; callback/failure coverage remains to be extended.
- [x] Deploy the tested ACON and M3 market contracts to Sepolia and publish their addresses/blocks.
- [x] Execute and verify a live guarded buy, including exact payment, positions, confirmations, and `TradeExecuted` decoding.
- [ ] In M4, implement oracle proposal/challenge state transitions.
- [ ] After exact M4 ABI freeze, implement the PR #28-approved resolver protocol: Safe-administered eligibility, snapshotted candidate pools, Chainlink VRF with stale-callback rejection, address-level conflicts, two 48-hour voting rounds, three-of-five quorum, fixed seven-day selection deadlines, and finalization/VOID.
- [ ] In M4, implement settlement, VOID behavior, and single-claim payout protection.
- [ ] Maintain unit/security tests, deployment tests, static checks, and contract CI.

Validation for the deployed `6e30d51` contract source includes Foundry format/build/script checks and 39 passing tests, runtime-bytecode comparison against Sepolia, and the confirmed ten-share YES buy. The consolidated workspace also passed 52 backend tests, 74 frontend tests, TypeScript checking, and the frontend production build. The stateful invariants exercise LMSR math, not the integrated token/market; intervening-trade stale quotes, token callbacks/failure rollback, and multi-account/multi-market accounting remain coverage follow-ups. Live Sepolia event retrieval/decoding, local worker/Supabase/API reconciliation, and the complete Anvil application flow passed; hosted worker/API/frontend acceptance remains pending.

### Matthew: LMSR economics

- [x] Implement `LMSR.sol` using 1e18 fixed-point arithmetic and `b = 50e18`.
- [x] Enforce minimum creator subsidy `ceil(b * ln(2)) = 34,657,359,027,997,265,471` base units.
- [x] Implement consistent quote/execution rounding for binary YES/NO buys.
- [x] Prove or test bounded-loss, monotonic-price, conservation/accounting, and extreme-input behavior.
- [x] Add unit, fuzz, and invariant tests for math and accounting.
- [ ] Define sell behavior only when the team begins the deferred sell scope.
- [ ] Define resolution, VOID, and payout accounting with Benny for M4.
- [ ] Keep trading and platform fees out of scope.

### Yudhveer: backend, database, indexer, oracle operations

- [ ] Complete the M3 queue above.
- [ ] Replace deprecated fake sample data in product flows after Adriel switches to indexed APIs.
- [ ] Add monitoring and recovery documentation for the API, worker, RPC, and database.
- [ ] After the proposal/challenge ABI freezes, add a deterministic result-provider interface and mock provider tests.
- [ ] Keep result fetching separate from transaction signing; use a least-privilege proposer key only on the server.
- [ ] In M4, index proposal, challenge, resolver, finalization, VOID, and payout events.
- [ ] In M4, expose resolver and settlement history/status without making PostgreSQL authoritative.
- [ ] Add reconciliation checks between database projections and sampled on-chain state.

### Shared integration, release, and course artifacts

- [x] Decide and document the 18-decimal ACON testnet payment asset.
- [ ] Freeze every cross-layer ABI/version before dependent releases.
- [x] Document and verify a reproducible local cross-layer integration flow; an automated CI job remains a follow-up.
- [x] Exercise the funded deployer wallet and documented ACON faucet/approval procedure; fund additional frontend demo wallets as needed.
- [ ] Document environment variables, secret ownership, rotation, and revocation.
- [x] Record deployment addresses, blocks, exact-build ABIs, and creation/trade examples in the validated public manifest.
- [x] Validate the local live demo from a fresh browser/session; repeat immediately before the presentation and repeat on hosted Sepolia if that is the claimed deployment.
- [ ] Update architecture, design rationale, test results, user guide, developer guide, and presentation claims.
- [ ] Complete accessibility, error-state, security, and regression testing before final release.
- [ ] Triage the 2026-10-22 frontend production dependency audit (23 moderate, 2 high, 0 critical), update compatible transitive packages, and rerun wallet/trading integration before a public release.

## Resolver And Oracle Scope

The resolver committee is **not required for Yudhveer's Milestone 3 implementation**. Benny's Solidity contracts must authoritatively select resolvers, reject conflicts, count votes, apply quorum/timeouts, and finalize or void markets. Yudhveer later indexes those emitted facts and exposes them through FastAPI; PostgreSQL must never select a committee or decide an outcome.

The PR #28-approved M4 design assigns administration to a 2-of-3 Sepolia Safe, uses Chainlink VRF v2.5 and test LINK, and excludes creator, fixture registrar, proposer, challenger, trader, position holder, and resolver admin addresses. Each selection round has a fixed seven-day deadline and candidate snapshot; 30-minute retries cannot extend it. Only the current request ID can install a committee; stale/duplicate/mismatched/late callbacks do nothing. Three matching direct votes in 48 hours finalize YES/NO or void on VOID; round 1 without quorum opens one replacement round and round 2 without quorum ends VOID. Exact contract/event ABI types must freeze before dependent implementation merges.

For M3, Yudhveer may implement a deterministic mock `ResultProvider` boundary after the trading path is stable. A production esports provider, an outcome-signing service, challenges, and resolver execution remain M4 work.

## Work That Must Not Be Guessed

Agents must stop and obtain a team decision before committing any of these as authoritative behavior:

- payment asset or token decimals;
- a changed enum order, function signature, event signature, or numeric unit;
- implementation of, or any authoritative change to, the decided resolver eligibility, randomness, snapshot, request-identity, conflict, quorum, timeout, or fallback rules before the exact ABI freeze;
- which esports source is authoritative and what evidence/finality means;
- private-key custody, signer permissions, or production secret placement;
- a production migration or deployment requiring shared credentials.
