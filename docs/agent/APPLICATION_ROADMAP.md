# AC_ON Application Roadmap

This is the canonical implementation checklist for coding agents and team members. It records what exists, what remains, who owns each area, and whether work can proceed without another team decision. Detailed milestone scope remains in `milestones/` and current assignments remain in `TASKS.md`.

Last reviewed: 2026-10-21 on `dev` at merge commit `6e30d51`.

PRs #10, #12, #13, #14, #15, and #16 are merged into `dev`. This includes the database/indexer/API foundation, approved M3 trading interface, bounded LMSR library, RPC/ABI worker, ACON token, and guarded-buy market integration. Fresh Sepolia deployment and live cross-layer validation are still pending.

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
| Contracts | ACON faucet/token, atomic creator subsidy, LMSR quotes, guarded buys, share balances, and complete trade events. | Merged into `dev` in PR #16; not yet a fresh Sepolia deployment. Sells/resolution/payouts remain deferred. |
| Backend API | Health, deprecated sample data, and indexed market/trade/status endpoints. | Merged into `dev`; not yet deployed with live indexed data. |
| Database | Alembic models for indexed contracts, checkpoints, processed logs, markets, and trades. | Merged into `dev`; revision `20261018_0001` applied to the configured Supabase database on 2026-10-21. Indexer tables are empty pending deployment. |
| Indexer | Confirmed-log projections, atomic checkpoints, idempotency, restart/reorg recovery, JSON-RPC transport, polling worker, and strict ABI decoder. | Foundation and RPC worker merged; live validation awaits the M3 contract handoff. |
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
5. **Done:** Benny's ACON/LMSR integration merged in PR #16. Confirm the generated ABI with consumers, then deploy and publish the handoff.

### PR #16 source-interface consumer check

The merged Solidity `MarketCreated` and `TradeExecuted` declarations match the backend decoder's required field names, types, order, and indexed positions. The backend's current fixtures exercise those event shapes, but they are hand-built; the exact compiler-generated ABI and deployed log fixtures remain a handoff item. The frontend still has the M2 address and four-output `getMarket` ABI. The M3 contract returns six values in the order question, deadline, state, creator, YES quantity, NO quantity; the market ID comes from the call argument or event rather than a return value. No contract interface change is made in this check.

The indexer status API reports block lag against its last observed head and now exposes `updated_at` for detecting a stopped worker. Frontend freshness work must consider both: a stopped worker with a once-current checkpoint can still report zero lag. Backend commit `edfc7f9` on local `dev` compares incremental indexing with a full replay into a separate empty database and exercises database-outage responses, transaction lookup, and stale status timestamps. Remote `dev` still needs the normal GitHub integration once authentication is restored.

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
| 4 | Benny | Integrate market creation, creator subsidy, quote, guarded buy, balances, and complete events. | Done | Merged in PR #16; generated ABI handoff and additional security coverage remain. |
| 5 | Yudhveer | Implement JSON-RPC transport, polling worker, backfill, retries, range splitting, and operational logging. | Done | Merged in PR #15; live deployment validation remains. |
| 6 | Yudhveer | Validate the ABI decoder and live market/trade projections. | Partial | Decoder exists; live validation needs compiled ABI, new address, and deployment block from Benny. |
| 7 | Benny | Deploy the integrated contract to Sepolia and publish its handoff record. | Pending | Deployment script implemented and simulated locally; needs review, funded wallet, and fresh deployment. |
| 8 | Yudhveer | Apply migrations and deploy API/worker using Render and Supabase. | Partial | Deployment preparation is ready; execution needs hosted credentials and the final contract handoff. |
| 9 | Adriel | Implement quote/buy UI and submitted/mined/indexed states. | Partial | UI state work can start; live calls need the frozen ABI and deployed contract. |
| 10 | Team | Run and document the end-to-end buy demonstration. | Blocked | Requires steps 1-9 and funded Sepolia wallets/test tokens. |
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
- [x] Add a checked-in ABI-version convention and deployment manifest template without committing secrets; the real manifest still awaits Benny's deployment record.
- [x] Confirm pagination limits, validation, empty responses, metadata, and lag reporting on the indexed APIs with local tests.

### Can be scaffolded now but needs a final handoff

- [x] Build ABI-driven decoder dispatch that maps known event topics to normalized `ChainLog` values and rejects ABIs missing the approved events.
- [x] Prepare hand-built decoder fixtures for the approved events; add exact Foundry-generated fixtures after the deployed ABI freezes.
- [x] Prepare the Alembic migration and read-only staging verification queries; revision `20261018_0001` was applied to the configured Supabase database on 2026-10-21 after backing up its three sample rows.
- [x] Prepare Render service/worker settings in the deployment runbook; live deployment requires RPC/database secrets and the contract deployment record.
- [x] Prepare a read-only Sepolia creation/trade-to-API smoke test; running it requires the final ABI, address, block, example transactions, and live API.
- [ ] Coordinate Adriel's API client against the existing OpenAPI endpoints; real UI verification requires indexed Sepolia data.

### Blocked inputs

- [ ] Compiled ABI from the exact Solidity commit deployed to Sepolia.
- [ ] Final Sepolia contract address and deployment transaction/block.
- [x] Contract behavior documented for creation subsidy, guarded buy, deadline, enum-decoder rejection, balance/allowance, and slippage reverts; consumer review remains.
- [x] ACON faucet authorization and demo-token distribution procedure documented in `contracts/README.md`; live accounts still need funding.
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

Yudhveer may propose event fields because the indexer consumes them. Benny must implement and generate the final ABI, Matthew must validate LMSR quantities and units, and Adriel must validate frontend needs. The handoff is complete only when all of the following are recorded:

- [ ] Git commit of the deployed contract source.
- [ ] Chain ID (`11155111` for Sepolia).
- [ ] Checksummed contract address.
- [ ] Deployment transaction hash and deployment block.
- [ ] Generated JSON ABI from that exact build.
- [ ] ABI/version label used by the indexer.
- [ ] Function inputs, outputs, custom errors, and access restrictions.
- [ ] Event names, indexed parameters, non-indexed parameters, and exact Solidity types.
- [ ] Market-state and outcome-enum numeric order.
- [ ] Unit for every quantity: token base units, 1e18 fixed point, shares, or Unix seconds.
- [ ] Payment token address/decimals or an explicit statement that native Sepolia ETH is used.
- [ ] Example successful creation and trade transaction hashes for integration fixtures.

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

These declarations match the approved PR #12 decision record and are implemented in contract commit 4c57dc0. All share, cost, and LMSR quantity fields use 1e18 base units. The decoder projects a newly created market as `OPEN` and fails startup if the supplied ABI does not contain these exact event shapes. A compiled ABI and deployment-specific handoff are still needed before live validation.

The implemented `getMarket` returns six fields, with the market ID supplied by its argument/event rather than included in the return tuple. Confirm this representation with Adriel and Yudhveer against the approved identifier requirement. Exact signatures, units, errors, and current test coverage are in [`../../contracts/README.md`](../../contracts/README.md).

## Remaining Application Work By Owner

### Adriel: frontend and Web3

- [ ] Browse indexed markets and display explicit indexed-data freshness.
- [ ] Create a market through the wallet when the contract interface exists.
- [ ] Request an on-chain LMSR quote and submit a guarded buy with `maxCost`.
- [ ] Display wallet rejection, submitted, mined, reverted, awaiting-indexer, and indexed states.
- [ ] Display YES/NO positions using authoritative contract reads where appropriate.
- [ ] Add market status, challenge, resolver vote, claim, and portfolio flows in M4.
- [ ] Add component tests and an end-to-end wallet/contract/API test path.
- [ ] Configure Vercel without exposing server-only secrets.

### Benny: lifecycle and resolver contracts

- [ ] Complete consumer review of the implemented M3 ABI and publish the exact-build ABI handoff.
- [x] Implement market creation, subsidy enforcement, deadline/state rules, quote integration, guarded buy, balances, and events (merged in PR #16).
- [x] Use caller-only token payments/positions, balance/allowance checks, custom errors, and a shared reentrancy guard across token transfers. State updates follow successful transfers under the guard; callback/failure coverage remains to be extended.
- [ ] Deploy the tested M3 contract to Sepolia and publish the complete handoff.
- [ ] In M4, implement oracle proposal/challenge state transitions.
- [ ] In M4, implement resolver eligibility, conflict exclusions, selection/randomness, voting, quorum, timeouts, and finalization.
- [ ] In M4, implement settlement, VOID behavior, and single-claim payout protection.
- [ ] Maintain unit/security tests, deployment tests, static checks, and contract CI.

Local checks for 4c57dc0 passed: Foundry format/build/script build and 39 tests, plus a local deployment simulation. The existing stateful invariants exercise LMSR math, not the integrated token/market. Additional validation should cover an intervening-trade stale quote, token callbacks/failure rollback, and multi-account/multi-market accounting. Live Sepolia and frontend/indexer acceptance have not been demonstrated for this revision.

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
- [ ] Establish test wallets and a test-token/faucet procedure without sharing private keys.
- [ ] Document environment variables, secret ownership, rotation, and revocation.
- [ ] Record deployment addresses and blocks in a non-secret deployment manifest.
- [ ] Validate the live demo from a fresh browser/session before each milestone presentation.
- [ ] Update architecture, design rationale, test results, user guide, developer guide, and presentation claims.
- [ ] Complete accessibility, error-state, security, and regression testing before final release.

## Resolver And Oracle Scope

The resolver committee is **not required for Yudhveer's Milestone 3 implementation**. Benny's Solidity contracts must authoritatively select resolvers, reject conflicts, count votes, apply quorum/timeouts, and finalize or void markets. Yudhveer later indexes those emitted facts and exposes them through FastAPI; PostgreSQL must never select a committee or decide an outcome.

For M3, Yudhveer may implement a deterministic mock `ResultProvider` boundary after the trading path is stable. A production esports provider, an outcome-signing service, challenges, and resolver execution are M4 work and remain blocked until the proposal/challenge/resolution ABI and security rules are approved.

## Work That Must Not Be Guessed

Agents must stop and obtain a team decision before committing any of these as authoritative behavior:

- payment asset or token decimals;
- a changed enum order, function signature, event signature, or numeric unit;
- resolver eligibility, randomness, conflict, quorum, timeout, or fallback rules;
- which esports source is authoritative and what evidence/finality means;
- private-key custody, signer permissions, or production secret placement;
- a production migration or deployment requiring shared credentials.
