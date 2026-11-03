# Milestone 4: Feature-Complete

Status: M4 target design was approved in PR #28. PRs #37/#38 are merged with the locally verified M4 contract, exact ABI/event artifacts, deployment tooling, and economic proof/invariants. PRs #30-#34 and #39 provide the merged off-chain fixture and reviewed PandaScore foundations. The current integration branch implements production registrar/proposer gateways, M4 projections and `/api/v2`, plus frontend buy/sell history wiring. Fresh Sepolia deployment, Safe/VRF and service-role handoff, credentialed PandaScore/Sepolia smoke, and full cross-layer acceptance remain unfinished.

The PandaScore adapter supports Valorant, CS2, and Rainbow Six Siege, but live ingestion remains disabled until written permission and team approval confirm this educational test-token use. Manual JSON/mock ingestion remains the accepted no-cost path. PandaScore observations are non-authoritative; an operator must attach independently reviewed evidence to the exact observation before it can feed a proposal intent.

The merged backend stack stores immutable signed fixture snapshots and provides mock-gateway registrar/proposer state machines with audit transitions, bounded retries, uncertain-submission quarantine, correction review, and append-only operator approvals. It also exposes registration-request status and the active worker ABI version. These are off-chain workflow boundaries: no production signer or confirmed M4 registration is configured, and importing or approving a fixture does not create a market. The [backend API handoff](../interfaces/M4_BACKEND_API.md) specifies EOA-only request signing and frontend polling.

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
| Benny - contracts/deployment | M4 lifecycle, resolver, payout, and security implementation is merged in PR #37 with local Foundry/Anvil evidence and exact ABI/event artifacts; Matthew's economics proof is merged in #38. Complete a fresh Sepolia deployment, Safe/VRF ownership, service-role grants, deployer-admin renunciation, manifest, and focused transaction smoke. | Merged code/ABI; requires team-controlled Safe, funded VRF subscription, eligible resolver pool, and deployment credentials. |
| Matthew - economics/accounting | Buy/sell/payout collateral proof, rounding regression vector, and stateful invariants are merged in PR #38 and included in the locally verified contract stack. Reconcile the accounting against integrated Anvil journeys and claims. | Full local lifecycle integration. |
| Adriel - frontend/wallet | Complete and test M4 fixture, market, trading, resolution, and portfolio UI against the merged ABI and backend APIs. PR #40 contains contract actions and stacked PR #43 contains portfolio work; both remain under review. | Backend APIs, M4 deployment, registered fixtures, and component/end-to-end evidence. |
| Yudhveer - backend/oracle/operations | Fixture/result sources, signed EOA requests, independent review, registrar/proposer processes, M4 projections/migration, `/api/v2`, and operations documentation are implemented on the current integration branch. Complete credentialed PandaScore, Anvil cross-layer, and Sepolia transaction evidence. | Live transactions require the fresh M4 deployment, private configuration, and narrow role grants. |
| Whole team - interfaces/integration | ABI and economic decisions are frozen in merged #37/#38. Complete deployment/role handoff, review subsystem PRs, run full Anvil and focused Sepolia journeys, reconcile projections/API/UI, update evidence, and rehearse. | Fresh deployment, Safe/VRF, eligible resolver pool, and integrated subsystems. |

## Owner Handoffs And Roadblocks

An owner can start the work in the second column now. A dependency in the third column blocks only the named integration or release step, not the entire owner's assignment. The owner in the fourth column publishes the handoff in a PR or versioned deployment record so the next person can work without guessing. The merged M4 contract/ABI is locally verified; deployment, roles, and cross-layer handoffs remain separate acceptance items.

| Owner | Can start now | Wait for before dependent work or release | Handoff that clears the wait |
|---|---|---|---|
| Benny | Publish M4 deployment manifest and transaction smoke from the merged contract/ABI; configure Safe, VRF, and narrow roles. | Team Safe, funded VRF subscription, eligible resolver pool, deployment credentials. | Sepolia deployment block/addresses, role receipts, and focused smoke evidence. |
| Matthew | Review integrated payout/claim journeys against the merged economic proof and invariants. | Full Anvil lifecycle evidence. | Record accounting reconciliation and any deviations in the proof. |
| Adriel | Continue UI work against merged ABI and documented API mocks; PR #40/#43 are in review. | Backend lifecycle APIs and fresh M4 deployment for live writes; integrated services for end-to-end tests. | Component/browser test evidence and API/ABI consumer sign-off. |
| Yudhveer | Use merged M4 ABI/event fixtures; implement event projections, read APIs, and signer gateways against Anvil. | Fresh M4 deployment and narrow role grants for Sepolia transactions. | Migration/rebuild, signer reconciliation/rotation docs, replay tests, and Anvil/Sepolia evidence. |
| Whole team | Complete Safe/VRF and service-role setup; review integrated subsystem PRs; prepare the Anvil harness and acceptance evidence checklist. | Integrated contract, backend, and frontend PRs; fresh M4 Sepolia deployment for required smoke. Hosted credentials/services are needed only for the stretch goal. | Record local lifecycle comparisons, focused Sepolia transaction/indexing evidence, and any remaining release gaps. |

The exact M4 ABI and economic/accounting model are available in merged PRs #37/#38. The next shared gate is the fresh M4 deployment and role/VRF handoff. Use the merged exact ABI and Anvil fixtures for integration; do not claim live registration or proposals until signer gateways and role grants are verified.

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
