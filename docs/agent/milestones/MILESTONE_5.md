# Milestone 5: Testing and Integration

Status: active planning. Milestone 4 is merged to `main`; M5 hardens and publicly deploys
that frozen feature set. Product features, contract redesign, API expansion, and network
migration are out of scope unless integration testing proves a release-blocking defect.

## Course Deliverables

The presentation reports integration results, defects and fixes, and the deployment plan.
Repository artifacts are the consolidated [integration results](../testing/M5_INTEGRATION_RESULTS.md),
[defect ledger](../testing/M5_DEFECT_LOG.md), [deployment plan](../M5_DEPLOYMENT_PLAN.md),
and draft [user](../../USER_GUIDE.md) and [developer](../../DEVELOPER_GUIDE.md) guides.

M5 acceptance requires a public Vercel frontend, Render API and three isolated workers,
Supabase PostgreSQL, the operator-gated PandaScore adapter, and the existing Ethereum Sepolia
deployment to operate together. Long timeout, replacement-round, and VOID paths remain
time-controlled Anvil evidence and must be labeled as such.

## Frozen Baseline And Boundaries

- Reuse the Sepolia deployment in `deployments/sepolia-2026-11-02` and its frozen ABI.
- Keep `/api/v2`, fixture APIs, database semantics, and Team A/YES mapping compatible.
- Run one indexer, one registrar, and one proposer as separate processes and accounts.
- Store hosted secrets only in managed secret stores. Never host Safe-owner or resolver keys.
- Playwright automates public read-only journeys. MetaMask writes use disposable testnet wallets.
- NGINX, fees, relayed voting, new contracts, and product redesign are outside M5.

## Ownership And Acceptance Evidence

| Owner | Assignment | Required handoff |
|---|---|---|
| Adriel | Deploy and validate Vercel; add read-only Playwright journeys; run manual wallet/browser tests; draft the user guide and capture sanitized screenshots. | Public URL, browser results, screenshots, and user-guide draft. |
| Benny | Revalidate manifest, ABI/bytecode, Safe roles, resolver pool, VRF, and balances; rerun Foundry/security checks; coordinate public dispute/VRF/vote/claim transactions. | Verification report, transaction hashes/blocks/request ID, and contract rollback criteria. |
| Matthew | Reconcile public buy/sell, bond, liabilities, payouts, duplicate claims, and creator surplus; rerun economic properties and document parameters/limitations. | Accounting comparison and economic test summary linked to public receipts. |
| Yudhveer | Deploy Render API/indexer/registrar/proposer and Supabase migrations; add public smoke and PostgreSQL CI coverage; verify recovery; draft the developer guide; maintain evidence/defect ledgers. | Public API/worker evidence, migration/recovery record, smoke output, and developer-guide draft. |
| Whole team | Run public and Anvil acceptance, triage defects, rerun CI, and rehearse results/bugs/deployment presentation. | Completed matrices with linked fixes or explicitly accepted residual risks. |

## One-Week Delivery Order

1. **Day 1 — planning and security:** merge the planning PR; confirm service access;
   abandon the exposed disposable challenger wallet; back up Supabase and record revision/counts.
2. **Day 2 — public services:** deploy Render and Vercel; apply migrations; verify health,
   CORS, chain/ABI/address agreement, indexer freshness, and read-only Playwright journeys.
3. **Day 3 — trading:** register a reviewed fixture, create/fund a market, buy and sell,
   then compare receipts, balances, projections, API output, and UI state.
4. **Day 4 — dispute:** submit a reviewed result, challenge it, record a real VRF request and
   callback, identify five resolvers, obtain three matching votes, and verify settlement.
5. **Day 5 — claims and recovery:** claim, reject a duplicate claim, reconcile bonds,
   liabilities and surplus, restart all services, and run time-controlled Anvil paths.
6. **Days 6–7 — release evidence:** fix defects with regression tests, rerun all checks,
   finish draft guides and deployment/rollback records, and rehearse the presentation.

Use two public markets when real schedules permit: one unchallenged and one disputed. If only
one suitable fixture exists, prioritize the public disputed/VRF lifecycle and retain the normal,
timeout, replacement, and VOID journeys as clearly labeled Anvil evidence.

## Test Matrix

| Layer | Required M5 verification |
|---|---|
| Contracts/security | Foundry unit/fuzz/invariant, six Anvil journeys, Slither, coverage, ABI/source/runtime checks, manifest/role/VRF verification. |
| Economics | Quote/payment/proceeds, rounding/extremes, collateral, bond, remaining liability, winning/VOID payout, duplicate claim, and surplus reconciliation. |
| Backend/data | SQLite unit suite plus PostgreSQL migration, 78-digit values, replay/rebuild preservation, signer reconciliation, provider failures, and Supabase smoke. |
| Indexer | Confirmations, duplicate/reordered logs, restart, missed ranges, RPC retry, stale status, reorg repair, rebuild equality, and public receipt/API agreement. |
| Frontend | Vitest/typecheck/build, public Playwright reads, mobile/desktop checks, CORS/console failures, and manual MetaMask write states. |
| Public end to end | Review/registration, creation/funding, buy/sell, indexing, proposal, challenge, real VRF, committee, votes, settlement, claim/rejection, and surplus. |

Every result records environment, UTC time, actor role, fixture/market, transaction/block,
contract state, database/API result, UI result, screenshot/evidence link, status, and defect ID.

## PR Boundaries

1. `docs/m5-testing-integration`: planning, assignments, evidence templates, and draft guides.
2. Backend deployment/testing PR: Render configuration, public smoke, PostgreSQL CI, recovery docs.
3. Frontend deployment/testing PR: Vercel configuration, Playwright reads, user-guide updates.
4. Contract/economics evidence PR: reproducible verification and accounting results; no contract
   change unless a separately reviewed blocker is proven.
5. Final integration PR: defect fixes, completed evidence, presentation material, and residual risks.

Each code PR updates its affected tests, guide, deployment/recovery instructions, results rows,
and defect entry. Do not mark a row passed from an implementation claim alone.

## Exit Criteria

- Public Vercel, Render, Supabase, Sepolia, and—only after written permission is verified—PandaScore
  components communicate successfully.
- Required CI, PostgreSQL, public smoke, and read-only browser tests pass.
- Public evidence reaches real VRF selection, three-vote settlement, and payout.
- Long timeout/replacement/VOID paths pass on Anvil and are labeled local.
- Every defect has a fix and regression test or an accepted residual-risk disposition.
- Draft guides reproduce normal use, setup, deployment, monitoring, recovery, and rotation.
- Presentation results distinguish CI, local Anvil, public Sepolia, and manual-browser evidence.

## Assumptions And Blockers

- Render capacity supports one web service and three persistent workers.
- Vercel, Supabase, RPC, PandaScore, Safe, VRF, and resolver access is available privately.
- The existing Sepolia deployment remains authoritative unless a contract blocker is proven.
- Credentials, funding, real match timing, and public-chain deadlines may block an evidence row;
  record the block rather than replacing it with an unsupported claim.
