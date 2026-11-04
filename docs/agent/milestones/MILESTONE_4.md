# Milestone 4: Feature-Complete

Status: complete and promoted to `main` in PR #49. The feature-complete contract, economics,
frontend, backend, indexer, signer gateways, migrations, PandaScore adapter, frozen ABI, deployment
manifest, and operations runbook are merged. The fresh Sepolia deployment, Safe/VRF ownership,
resolver pool, and narrow service-role handoff are recorded. Full public Vercel/Render integration
and the remaining Sepolia sell/dispute/VRF/vote/claim evidence are Milestone 5 work.

The PandaScore adapter supports Valorant, CS2, and Rainbow Six Siege and is enabled only in a
private approved-use environment. Manual JSON/mock ingestion remains the deterministic recovery
path. PandaScore observations are non-authoritative; an operator must attach independently reviewed
evidence to the exact observation before it can feed a proposal intent.

The merged backend stack stores immutable signed fixture snapshots and provides production
registrar/proposer gateways with audit transitions, bounded retries, uncertain-submission
quarantine, correction review, and append-only approvals. Importing or approving a fixture still
does not create a market. The [backend API handoff](../interfaces/M4_BACKEND_API.md) specifies
EOA-only request signing and frontend polling.

Backend tests cover fixture imports, EOA replay/expiry, immutable snapshots, duplicate/rate limits, real-gateway ABI encoding and confirmation handling, uncertain submissions, correction review, migration upgrades, exact M4 event fixtures, lifecycle/portfolio projections, provider parsing, independent-evidence enforcement, and preservation of source/signer records during rebuilds. Live gateway transactions and Sepolia cross-layer acceptance still depend on the finalized deployment and private configuration handoff.

## Course Goal And Acceptance

Demonstrate the complete planned feature set, explain trade-offs, present a full testing and integration plan, and deliver final-design documentation. M4 acceptance requires complete normal, disputed, timeout, VOID, and claim journeys locally on Anvil; component tests; a documented full test plan; final ABI/design alignment; and a fresh Sepolia contract deployment with focused transaction smoke tests. Full public Vercel/Render/Supabase/Sepolia integration is an M4 stretch target, with unfinished hosting due in M5. Local Anvil exercises time-dependent paths that cannot finish during a short live demo.

Feature complete means users can browse verified esports fixtures, create and fund multiple markets, buy and sell YES/NO shares, inspect positions and trade history, challenge proposed outcomes, vote if selected as resolvers, and claim winning or VOID payouts. Market lifecycle, resolver selection/votes, collateral, and payouts are authoritative in Solidity. PostgreSQL and FastAPI expose derived history and status. The frontend must not claim that an indexed read or an esports provider independently settles a market.

## Fixture And Result Boundary

The required no-cost path uses a deterministic mock and a manual JSON fixture/result adapter with organizer evidence URL/hash. PandaScore is optional and disabled until its written permission confirms this test-token prediction use; the team will not purchase a paid plan. The restricted registrar records selected fixture IDs, Team A/YES and Team B/NO, and scheduled start on-chain. One user-funded market is allowed per registered fixture. Importing a fixture does **not** create a market, and the contract cannot independently prove source truth. A market deadline is at least 15 minutes before the scheduled start; early closure may shorten but never extend trading. No proposal within seven days of the trading deadline opens permissionless resolver selection.

The result adapter and signer are separate components. A least-privilege proposer may submit immutable YES, NO, or VOID with evidence, never settle a challenged market or select resolvers. Corrections use challenge/voting, canceled or unsupported results propose VOID, and a seven-day absence of proposal opens resolver selection. No public endpoint accepts arbitrary outcomes for signing. Secrets stay out of Git/browser; a 2-of-3 Sepolia Safe controlled by Benny, Matthew, and Adriel holds administration and VRF subscription ownership while Yudhveer's registrar and proposer keys have narrow roles.

## Work Distribution

| Owner | Implementation and validation assignment | Required handoff |
|---|---|---|
| Benny - contracts/deployment | M4 lifecycle, resolver, payout, security implementation, deployment, Safe/VRF ownership, roles, resolver pool, manifest, and focused smoke were completed. | Remaining full-lifecycle Sepolia evidence moved to M5. |
| Matthew - economics/accounting | Buy/sell/payout collateral proof, rounding regression vector, and stateful invariants are merged in PR #38 and included in the locally verified contract stack. Reconcile the accounting against integrated Anvil journeys and claims. | Full local lifecycle integration. |
| Adriel - frontend/wallet | M4 fixture, market, trading, resolution, claim, and portfolio UI merged in PRs #40/#43 and the M4 release. | Public Vercel/browser verification moved to M5. |
| Yudhveer - backend/oracle/operations | Fixture/results, independent review, registrar/proposer, M4 projections/migration, `/api/v2`, PandaScore, and operations documentation merged in PR #47. | Public Render/Supabase operation and recovery evidence moved to M5. |
| Whole team - interfaces/integration | Frozen ABI/economics and integrated application were promoted to `main` in PR #49. | Public cross-layer lifecycle evidence moved to M5. |

## Owner Handoffs And Roadblocks

This matrix is retained as the historical M4 handoff. Its implementation and deployment gates were
completed; unfinished public hosting and full Sepolia lifecycle evidence are tracked in M5.

| Owner | Can start now | Wait for before dependent work or release | Handoff that clears the wait |
|---|---|---|---|
| Benny | Published M4 deployment manifest and configured Safe, VRF, resolver pool, and narrow roles. | Complete. | Sepolia deployment block/addresses, role receipts, and focused smoke evidence. |
| Matthew | Review integrated payout/claim journeys against the merged economic proof and invariants. | Full Anvil lifecycle evidence. | Record accounting reconciliation and any deviations in the proof. |
| Adriel | Merged M4 UI consumers and component tests. | Complete. | Public browser evidence continues in M5. |
| Yudhveer | Merged event projections, read APIs, signer gateways, migration/rebuild, and runbook. | Complete. | Public worker/recovery evidence continues in M5. |
| Whole team | Integrated and released the feature-complete M4 stack. | Complete. | Public hosting and remaining lifecycle evidence continue in M5. |

The exact M4 ABI, economic model, deployment, and post-setup manifest are frozen release inputs.
M5 consumers must use those artifacts and must not infer or redesign the interface.

## Dependencies And One-Week Integration Order

1. **Day 1 - deployment and access:** Use the merged exact ABI/economic proof; configure the Safe, VRF subscription, resolver pool, and separate registrar/proposer accounts. Record deployment and role handoff before live transaction smoke.
2. **Days 2-4 - integration:** Implement backend chain gateways, M4 projections/APIs, and frontend flows against the merged interface; each PR updates affected documentation and tests.
3. **Days 5-6 - integration:** Run local normal, disputed, no-proposal timeout, replacement, VOID, and claim flows. Deploy a fresh M4 Sepolia contract and versioned manifest; run focused transaction smoke. If hosting is ready, configure one hosted indexer, API/oracle, and frontend, then reconcile Sepolia transactions with indexed reads.
4. **Day 7 - release evidence:** Repair defects, rerun CI and Sepolia smoke, record hashes and API results, reconcile final-design docs, and rehearse. Record full public integration as a stretch result or M5 handoff.

The approved design and merged ABI do not by themselves prove end-to-end behavior. Manual JSON remains the required no-cost provider path. If VRF funding, eligible resolvers, or Sepolia smoke are unavailable, record the blocked acceptance item. Hosted services remain a stretch target, not an M4 blocker.

## Full Documented Test Plan

| Layer | Required scenarios | Evidence |
|---|---|---|
| Solidity/economics | Buy/sell quote and slippage, quantity/collateral conservation, creator subsidy/surplus, winning and VOID liabilities, rounding/extreme values, failed token transfer/reentrancy, duplicate claims, unauthorized role calls. | Foundry unit, fuzz, invariant, and security/static checks. |
| Fixture/oracle | Normalized mock/manual JSON fields and evidence, fixture-key identity, one-market rule, early close/postponement/cancellation, duplicate/invalid fixtures, source disagreement, immutable proposals, seven-day no-proposal path, retry/idempotency, proposer permission and compromised-key revocation. Optional PandaScore adapter tests only if permission is obtained. | Deterministic fixtures, parser tests, registrar/proposer integration tests. |
| Resolver | Registry add/remove, every address-level conflict, ten-wallet allowlist, snapshot stability, five distinct selections, 30-minute retry, current request identity, stale/duplicate/late callbacks, one vote per resolver, three YES/NO versus three VOID votes, replacement round and reuse fallback, seven-day selection and 48-hour voting deadlines, and claims after both outcomes. | Foundry unit/invariant tests and Anvil time-controlled journeys. |
| Indexer/API/database | All new event shapes and exact amounts, duplicate/reordered logs, checkpoint/restart, missed ranges, reorg/rebuild equality, fresh migration, stale worker and database/API failure, contract/API reconciliation. | Pytest and read-only cross-layer smoke evidence. |
| Frontend/wallet | Fixture browse/create, buy/sell, portfolio, 10 ACON challenge, selected-resolver vote, finalization/VOID claim, wrong chain, rejected/reverted writes, submitted/mined/indexed distinction, stale and unavailable reads; triage production dependencies before public release. | Vitest/component/browser tests, dependency audit, local Anvil flow; public browser run if stretch target lands. |
| End to end | Normal unchallenged result, challenged result with quorum, first-round failure/replacement, no-proposal timeout, VOID, and single-use claim; compare wallet receipts, chain state, indexer projections, API responses, and UI. | Automated local Anvil flow plus focused Sepolia deployment/transaction smoke; full public cross-layer evidence is stretch/M5. |

Use Anvil time control for 24-hour and longer timeouts. The required Sepolia deployment/transaction smoke uses real confirmations; if full public cross-layer hosting is attempted, pre-seed timed markets rather than implying they progressed during a short live presentation.

## Approval And Documentation Rules

The [M4 design decision](../interfaces/M4_FEATURE_COMPLETE_INTERFACE.md) was approved in merged PR #28; the exact M4 ABI and event fixtures were merged in PR #37, with economics proof and invariants in PR #38. The [M3 interface](../interfaces/M3_TRADING_INTERFACE.md) remains the deployed baseline. Use the merged artifacts for dependent implementation; do not describe the M4 interface as awaiting ABI freeze. Each implementation PR updates affected README/API/ABI, deployment, testing, and recovery docs. Current-state pages change to "implemented" only after verified code and integration evidence exist.
