# AC_ON Application Roadmap

This is the canonical implementation checklist for coding agents and team members. It records what exists, what remains, who owns each area, and whether work can proceed without another team decision. Detailed milestone scope remains in `milestones/` and current assignments remain in `TASKS.md`.

Last reviewed: 2026-10-21, covering the `68322ef` integration baseline and the deployment/trade handoff published in PR #19.

PRs #10, #12, #13, #14, #15, #16, #17, and #18 are merged into `dev`. This includes the database/indexer/API foundation, approved M3 trading interface, bounded LMSR library, RPC/ABI worker, ACON token, guarded-buy market integration, transaction lookup, and versioned handoff validation. ACON and PredictionMarket were deployed from `6e30d516669e51d7f3e4bff0d8670168da9b1f83`; market `0` and a ten-share YES buy are confirmed on Sepolia. Hosted database/indexer/API projections and the frontend end-to-end demo remain pending.

The canonical integration input is [`deployments/sepolia-m3.json`](../../deployments/sepolia-m3.json). The [deployment and trade record](../../contracts/deployments/sepolia-m3-2026-10-21/README.md) includes the exact-build ABIs, receipts, balance checks, and gas-estimation recovery. Market `0` stops accepting buys on **2026-10-28 at 17:01:12 UTC**; use a new funded market for a later demo.

## Status Key

- **Done**: implemented in the repository. A feature-branch item is not integrated until its pull request merges.
- **Ready**: can be implemented now with repository information already available.
- **Partial**: useful generic work can proceed, but final integration needs the listed handoff.
- **Pending**: implementation/preparation exists, but execution or verification has not happened yet.
- **Blocked**: implementation would guess an authoritative interface, secret, deployment, or protocol decision.
- **Deferred**: intentionally outside Milestone 3 unless the trading MVP finishes early.

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
| Frontend | Wallet connection, Sepolia balance, and a read of prototype market `0`. | On `dev`; no trading write or indexed API integration. |
| Contracts | ACON faucet/token, atomic creator subsidy, LMSR quotes, guarded buys, share balances, and complete trade events. | Deployed from PR #16 merge commit `6e30d51`; seeded market and live guarded buy verified. Sells/resolution/payouts remain deferred. |
| Backend API | Health, deprecated sample data, and indexed market/trade/status endpoints. | Merged into `dev`; not yet deployed with live indexed data. |
| Database | Alembic models for indexed contracts, checkpoints, processed logs, markets, and trades. | Revision `20261018_0001` was reported applied to the configured Supabase database on 2026-10-21, with empty indexer tables at that check. Hosted live projections remain to be verified. |
| Indexer | Confirmed-log projections, atomic checkpoints, idempotency, restart/reorg recovery, JSON-RPC transport, polling worker, and strict ABI decoder. | Live creation/trade retrieval and decoding passed; persistent hosted worker/database/API validation remains pending. |
| Oracle | Design boundary only. | Not implemented. |
| Resolver | Design and ownership boundary only. | Not implemented; Milestone 4 scope. |
| CI | Frontend build, backend migrations/tests, and Foundry format/build/tests. | Implemented; no cross-layer end-to-end job. |

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

### PR #16 source-interface consumer check

The merged Solidity `MarketCreated` and `TradeExecuted` declarations match the backend decoder's required field names, types, order, and indexed positions. Exact compiler-generated ABIs are in `deployments/abi/`, and the [live trade fixture](../../contracts/deployments/sepolia-m3-2026-10-21/guarded-buy.json) records the canonical log. Both creation and trade were fetched and decoded with the backend's real RPC client and ABI decoder. The frontend still has the M2 address and four-output `getMarket` ABI. The deployed M3 contract returns six values in the order question, deadline, state, creator, YES quantity, NO quantity; the market ID comes from the call argument or event rather than a return value. The current handoff validator accepts this six-output ABI; consumer review of the identifier representation remains a team follow-up.

The indexer status API reports block lag against its last observed head and exposes `updated_at` for detecting a stopped worker. Frontend freshness work must consider both: a stopped worker with a once-current checkpoint can still report zero lag. PR #17 merged into `dev` with full-replay equality coverage, database-outage responses, transaction lookup, and stale status timestamp checks. PR #18 merged the versioned deployment handoff and live smoke check. The populated manifest passes validation; running the hosted smoke check now requires the configured API/worker and API URL.

### Frontend backend-API handoff

After a wallet buy is mined successfully, use `GET /api/trades/by-transaction/{transaction_hash}` to check for its confirmed `TradeExecuted` projection. The path requires a `0x`-prefixed 32-byte hash; hex case is accepted and the response hash is lowercase. The response contains `transaction_hash` and an `items` array of trade objects, ordered by block and log index. An empty array with HTTP 200 means no matching trade is indexed yet; it does not prove the wallet transaction failed. Invalid hashes return HTTP 422. Database read failures return a server error, not an empty array.

Read `/api/indexer/status` alongside the lookup. Its `updated_at` is a UTC ISO 8601 timestamp for the checkpoint's last update, or `null` before the worker observes a head; successful head observations refresh it. Confirm `configured`, chain ID, and contract address match the wallet's deployed market. While waiting, check that the update is recent and `last_safe_block` has reached the mined receipt's block. The default two-confirmation worker normally has nonzero `lag_blocks`; a zero value alone does not establish freshness. If the safe checkpoint has passed the receipt block and the lookup is still empty, inspect the receipt and its logs for `TradeExecuted` or a deployment mismatch. The backend never submits buys. See [backend/README.md](../../backend/README.md#frontend-indexing-synchronization) for the endpoint details.

## Milestone 3 Definition Of Done

The MVP is complete when this path works live on Ethereum Sepolia:

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
| 6 | Yudhveer | Validate the ABI decoder and live market/trade projections. | Partial | Live RPC retrieval/decoding passed for both events; persistent projections and API reconciliation remain. |
| 7 | Benny | Deploy the integrated contract to Sepolia and publish its handoff record. | Done | Deployed from `6e30d51`, seeded market `0`, verified a guarded buy, and published the manifest/ABIs/evidence in PR #19. |
| 8 | Yudhveer | Apply migrations and deploy API/worker using Render and Supabase. | Partial | Migration reported applied; the validated handoff is available. Configure hosted processes and verify live indexed data. |
| 9 | Adriel | Implement quote/buy UI and submitted/mined/indexed states. | Partial | Deployed addresses, generated ABIs, and example trade are available; update the M2 frontend and connect the indexed APIs. |
| 10 | Team | Run and document the end-to-end buy demonstration. | Blocked | Contract smoke test passed; requires the trading UI and hosted indexer/API from steps 8-9. |
| 11 | Team | Update design documentation, test plan/results, and presentation. | Ready | Keep claims limited to behavior demonstrated from the integrated branch. |

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
- [ ] Coordinate Adriel's API client against the existing OpenAPI endpoints; real UI verification requires indexed Sepolia data.

### Provided and remaining inputs

- [x] Compiled ABIs from deployed source `6e30d516669e51d7f3e4bff0d8670168da9b1f83`, with validated versioned filenames and hashes.
- [x] Final Sepolia token/market addresses, deployment transactions/blocks, and successful creation/trade examples in `deployments/sepolia-m3.json`.
- [x] Contract behavior documented for creation subsidy, guarded buy, deadline, enum-decoder rejection, balance/allowance, and slippage reverts; consumer review remains.
- [x] ACON faucet/approval procedure documented and exercised by the deployer; additional frontend demo wallets need their own gas and faucet claim.
- [x] Supabase migration access was authorized for this session and the configured database migration was applied.
- [ ] Render access and the required RPC/database environment values for hosted deployment.

### Yudhveer M3 completion criteria

- [ ] A new deployment can be registered by chain ID, address, deployment block, and ABI version.
- [ ] Backfill begins at the configured deployment block and resumes from its database checkpoint.
- [ ] Confirmed `MarketCreated` and `TradeExecuted` logs decode and project exactly once.
- [ ] Database and checkpoint changes for a block batch commit atomically.
- [ ] Duplicate delivery, process restart, missed ranges, RPC failure, and a simulated reorganization pass automated tests.
- [ ] `/api/indexer/status` reports observed head, safe checkpoint, and lag.
- [ ] Market and trade endpoints return paginated derived data with source-chain metadata.
- [ ] Supabase can be rebuilt deterministically from canonical contract events.
- [ ] No wallet key, RPC credential, or database credential is stored in Git or returned through the API.

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

These declarations match the approved PR #12 decision record and were deployed from merge commit `6e30d51`. All share, cost, and LMSR quantity fields use 1e18 base units. The decoder projects a newly created market as `OPEN` and fails startup if the supplied ABI does not contain these exact event shapes. The published ABI and canonical live creation/trade logs passed decoder validation; hosted projection and API checks remain.

The implemented `getMarket` returns six fields, with the market ID supplied by its argument/event rather than included in the return tuple. Confirm this representation with Adriel and Yudhveer against the approved identifier requirement. Exact signatures, units, errors, and current test coverage are in [`../../contracts/README.md`](../../contracts/README.md).

## Remaining Application Work By Owner

### Adriel: frontend and Web3

- [ ] Browse indexed markets and display explicit indexed-data freshness.
- [ ] Add wallet-based market creation using the deployed subsidy-funded contract interface (optional for the core buy demo).
- [ ] Request an on-chain LMSR quote and submit a guarded buy with `maxCost`.
- [ ] Display wallet rejection, submitted, mined, reverted, awaiting-indexer, and indexed states.
- [ ] Display YES/NO positions using authoritative contract reads where appropriate.
- [ ] Add market status, challenge, resolver vote, claim, and portfolio flows in M4.
- [ ] Add component tests and an end-to-end wallet/contract/API test path.
- [ ] Configure Vercel without exposing server-only secrets.

### Benny: lifecycle and resolver contracts

- [x] Publish the exact-build ABI handoff with a validated manifest and live transaction evidence (PR #19).
- [ ] Complete consumer review of the deployed six-output `getMarket` ABI and identifier representation.
- [x] Implement market creation, subsidy enforcement, deadline/state rules, quote integration, guarded buy, balances, and events (merged in PR #16).
- [x] Use caller-only token payments/positions, balance/allowance checks, custom errors, and a shared reentrancy guard across token transfers. State updates follow successful transfers under the guard; callback/failure coverage remains to be extended.
- [x] Deploy the tested ACON and M3 market contracts to Sepolia and publish their addresses/blocks.
- [x] Execute and verify a live guarded buy, including exact payment, positions, confirmations, and `TradeExecuted` decoding.
- [ ] In M4, implement oracle proposal/challenge state transitions.
- [ ] In M4, implement the approved resolver protocol: multisignature-administered eligibility, Chainlink VRF selection, address-level conflict exclusions, two 48-hour voting rounds, three-of-five quorum, seven-day committee-formation fallback, and finalization.
- [ ] In M4, implement settlement, VOID behavior, and single-claim payout protection.
- [ ] Maintain unit/security tests, deployment tests, static checks, and contract CI.

Validation for the deployed `6e30d51` contract source includes Foundry format/build/script checks and 39 passing tests, runtime-bytecode comparison against Sepolia, and the confirmed ten-share YES buy. The consolidated workspace also passed 52 backend tests and the frontend build. The stateful invariants exercise LMSR math, not the integrated token/market; intervening-trade stale quotes, token callbacks/failure rollback, and multi-account/multi-market accounting remain coverage follow-ups. Live event retrieval/decoding passed; hosted database/indexer/API and frontend acceptance remain pending.

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
- [ ] Create a reproducible local or CI cross-layer integration harness.
- [x] Exercise the funded deployer wallet and documented ACON faucet/approval procedure; fund additional frontend demo wallets as needed.
- [ ] Document environment variables, secret ownership, rotation, and revocation.
- [x] Record deployment addresses, blocks, exact-build ABIs, and creation/trade examples in the validated public manifest.
- [ ] Validate the live demo from a fresh browser/session before each milestone presentation.
- [ ] Update architecture, design rationale, test results, user guide, developer guide, and presentation claims.
- [ ] Complete accessibility, error-state, security, and regression testing before final release.

## Resolver And Oracle Scope

The resolver committee is **not required for Yudhveer's Milestone 3 implementation**. Benny's Solidity contracts must authoritatively select resolvers, reject conflicts, count votes, apply quorum/timeouts, and finalize or void markets. Yudhveer later indexes those emitted facts and exposes them through FastAPI; PostgreSQL must never select a committee or decide an outcome.

The resolver design is approved for Milestone 4: a project-team multisignature wallet administers the on-chain allowlist; Chainlink VRF selects five distinct eligible resolvers; creator, proposer, challenger, trader, and position-holder addresses are excluded; three matching direct on-chain votes decide each 48-hour round; one replacement committee is allowed; and inability to form a committee within seven days or reach quorum in the replacement round ends in `VOID`. Direct voting does not require signature recovery. Any future relayed voting must support ECDSA and EIP-1271. Implementation remains blocked on the Milestone 4 contract/event ABI freeze, not on these protocol choices.

For M3, Yudhveer may implement a deterministic mock `ResultProvider` boundary after the trading path is stable. A production esports provider, an outcome-signing service, challenges, and resolver execution remain M4 work.

## Work That Must Not Be Guessed

Agents must stop and obtain a team decision before committing any of these as authoritative behavior:

- payment asset or token decimals;
- a changed enum order, function signature, event signature, or numeric unit;
- any change to the approved resolver eligibility, randomness, conflict, quorum, timeout, or fallback rules;
- which esports source is authoritative and what evidence/finality means;
- private-key custody, signer permissions, or production secret placement;
- a production migration or deployment requiring shared credentials.
