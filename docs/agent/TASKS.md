# Tasks

Use this file to coordinate current work. Official course artifacts may live outside the repo, but this list records who owns each slice so agents do not duplicate or drift.

## Historical Milestone 2 Course Artifact Assignments

| Owner | Area | Assignment | Repo Impact | Status |
|---|---|---|---|---|
| Adriel | coordination/frontend | Team roles, Section 4 frontend row, Section 6 prototype, README, submit | Keep top-level README and frontend prototype notes accurate. | assigned |
| Benny | diagrams/contracts/CI | Section 2 class diagram + market state diagram, Section 4 contracts row, CI pipeline | Add CI skeleton and keep contract architecture notes current. | assigned |
| Matthew | LMSR/requirements | Section 3 LMSR + liquidity funding rows, Section 2 trade sequence diagram, renumber requirements FR-01/NFR-01, claim-winnings story | Keep LMSR/trading assumptions aligned with future contract work. | assigned |
| Yudhveer | architecture/backend/trust | Section 1 architecture diagram with on/off-chain labels, oracle and resolver separation, Section 2 resolution sequence diagram, Section 3 trust model, Section 4 backend/DB rows, branch protection | Keep architecture/trust/backend notes aligned with implementation. | assigned |

## Historical Milestone 2 Coding Queue

| Priority | Owner | Subsystem | Task | Dependencies | Status |
|---|---|---|---|---|---|
| P0 | Yudhveer/team | repo | Create or confirm `dev` branch and branch protection rules. | GitHub permissions | ready |
| P0 | Benny | CI | Add GitHub Actions skeleton for frontend install/build. | package-lock present | done |
| P0 | Benny/Matthew | contracts | Add minimal Foundry scaffold. | team confirms layout | ready |
| P0 | Benny/Matthew | contracts | Add one simple sample market read and one simple write. | contract scaffold | ready |
| P0 | Adriel | frontend | Wire frontend to one contract read. | ABI/address from contracts | blocked |
| P0 | Adriel | frontend | Wire frontend to one contract write. | contract write function | blocked |
| P1 | Yudhveer | backend | Add minimal FastAPI app with `GET /health` and fake sample-match endpoints. | Python dependency choice | done |
| P1 | Yudhveer | database | Use Supabase PostgreSQL for Milestone 2 fake sample data via `DATABASE_URL`. | backend scaffold | done |
| P1 | Yudhveer/Benny | oracle/indexer | Document or scaffold basic event/oracle boundary. | contract event plan | ready |
| P1 | team | docs/demo | Keep README and Milestone 2 demo checklist current. | working prototype state | ready |

## Historical Milestone 2 Done

| Owner | Subsystem | Task | Status |
|---|---|---|---|
| team | frontend | Minimal wallet connect prototype with address and balance display. | done |
| team | docs | Initial agent planning docs and milestone structure. | done |

## Product Ownership: Milestones 3-6

These ownership areas remain stable through the final product. The active [Milestone 4 assignments](milestones/MILESTONE_4.md#work-distribution) below make the deliverables and handoffs more specific.

| Owner | Primary product ownership | Testing and deployment ownership |
|---|---|---|
| Adriel | Frontend and Web3 flows: browse/create markets, quote/trade, positions, challenges, resolver voting, claims, and transaction/indexer synchronization. | Vitest and frontend end-to-end coverage; Vercel deployment. |
| Benny | Solidity market lifecycle and authorization, resolver registry/selection/voting, settlement, claims, VOID behavior, contract events, and Sepolia deployment scripts. | Foundry unit/security tests, contract static analysis, and contract CI. |
| Matthew | `LMSR.sol`, 1e18 fixed-point arithmetic, `b = 50`, creator subsidy, buy/sell pricing, and payout/VOID accounting rules. Trading/platform fees are out of scope. | Foundry fuzz/invariant tests and economic/accounting documentation. |
| Yudhveer | FastAPI, PostgreSQL, event indexer, oracle providers/signer operations, resolver projections/APIs, replay/reorganization recovery, and trust/security documentation. | Pytest and cross-layer integration coverage; Render/Supabase deployment. |
| Team | ABI/event freezes, secrets policy, live demos, cross-layer acceptance, reports, and release validation. | Review required across subsystem boundaries. |

## Historical Milestone 3 MVP Queue

The guarded-buy implementation is complete and the full contract-to-indexer-to-API-to-frontend path has been verified on local Anvil. The remaining M3 integration task is hosted Sepolia acceptance. PR #22 records the earlier resolver proposal; the M4 decision set in PR #28 supersedes it for target design. Exact M4 event/function ABI types and approval names still need recording before dependent code merges.

The approved cross-layer freeze is documented in [`interfaces/M3_TRADING_INTERFACE.md`](interfaces/M3_TRADING_INTERFACE.md). Dependent contract, indexer, and frontend work must implement that interface or update the decision record through team review.

| Priority | Owner | Subsystem | Task | Dependencies | Status |
|---|---|---|---|---|---|
| P0 | team | interfaces | Freeze the payment asset, market/trade ABI, enum order, event fields, numeric units, and deployment handoff. | Team approval of the decision record | approved in PR #12 |
| P0 | Matthew | LMSR/contracts | Implement `LMSR.sol` with 1e18 precision, `b = 50`, creator subsidy `ceil(b * ln(2))`, quote/cost math, and economic invariants. | team review | merged in PR #13 |
| P0 | Benny | contracts | Integrate ACON subsidy collection, LMSR quotes, guarded YES/NO buy, positions, and `TradeExecuted`. | interface freeze and LMSR library | merged in PR #16; deployed from `6e30d51`; live ten-share YES buy verified; handoff published in PR #19 |
| P0 | Yudhveer | indexer/database | Implement migrations, unique event identity, atomic checkpoints, confirmation handling, deterministic rebuild, and reorg recovery. | hosted database/worker configuration and published M3 manifest | merged in PR #10; local Sepolia worker populated Supabase and passed API smoke check; hosted worker operation pending |
| P0 | Yudhveer | backend | Implement paginated indexed market/trade/status read APIs with derived-state metadata. | indexed schema | merged in PR #10 |
| P0 | Yudhveer | RPC worker | Implement validated JSON-RPC retrieval, bounded polling/retries/range splitting, ABI decoder boundary, clean shutdown, and deployment runbook. | persistent worker and API configuration | merged in PR #15; canonical creation/trade retrieval and decoding passed; hosted indexing pending |
| P1 | Yudhveer | deployment prep | Version the exact-build ABI, validate a public deployment manifest, verify API edge cases, and prepare a Sepolia smoke test. | configured hosted worker/API for cross-layer check | PR #18 merged; local Sepolia worker/Supabase/API smoke passed; repeat against hosted services later |
| P0 | Adriel | frontend | Implement quote/buy and submitted/mined/indexed UI states. | published M3 addresses/ABIs and indexed backend endpoints | merged in PR #20; M3 ABI/config, quote/buy, positions, freshness guard, and transaction states verified in the local Anvil flow |
| P1 | team | integration | Run the contract-to-indexer-to-API-to-frontend demo against the deployed M3 contracts. | hosted worker/API/frontend configuration | complete on local Anvil; hosted Sepolia acceptance remains pending |
| P1 | Yudhveer | oracle | Add provider and least-privilege signer boundaries with deterministic mock tests. | proposal/challenge ABI | blocked |
| P2 | Benny | resolver contracts | Implement authoritative eligibility, snapshotted candidate pools, current-request-only Chainlink VRF selection, conflict checks, two 48-hour voting rounds, three-of-five quorum, fixed seven-day committee deadlines, and finalization. | PR #28 team approval record and exact M4 ABI freeze | M4 target decided; implementation pending |
| P2 | Yudhveer | resolver backend | Index resolver events and expose committee, vote, quorum, and timeout status without making authoritative decisions. | resolver event interface | deferred to Milestone 4 |
| P2 | team | CI/tests | Add a cross-layer integration job or reproducible local integration harness. | working vertical slice | reproducible local flow documented and manually verified; automated cross-layer CI remains a follow-up |

Use the validated [`../../deployments/sepolia-m3.json`](../../deployments/sepolia-m3.json) for M3 addresses, blocks, versioned ABIs, and creation/trade transactions. The [deployment and live-buy evidence](../../contracts/deployments/sepolia-m3-2026-10-21/README.md) is published in PR #19. Market `0` stopped accepting trades on **2026-10-28 at 17:01:12 UTC**; use a newly funded market for any later trade demo. PR #20 updated the frontend to the M3 ABI and environment-driven addresses, including the six-output `getMarket` representation. Use MetaMask for Sepolia writes because Coinbase Smart Wallet does not support sending transactions on Ethereum Sepolia.

## Active Milestone 4 Feature-Complete Queue

Status: **M4 target assignments recorded; implementation pending**. The [M4 milestone](milestones/MILESTONE_4.md) contains detailed ownership/tests, and the [M4 design decision](interfaces/M4_FEATURE_COMPLETE_INTERFACE.md) supplies target rules. PR #28 still needs approving names and an exact ABI freeze. Full public application integration is an M4 stretch target and remains required in M5 if unfinished.

| Priority | Owner | Deliverable and acceptance evidence | Dependency | Status |
|---|---|---|---|---|
| P0 | Team | Record named approval of the supplied fixture, lifecycle, economics, challenge, resolver, hosting, and secrets decisions; freeze exact ABI argument types/indexed fields and deployment handoff. | VRF v2.5 test LINK/subscription, at least ten clean resolver addresses, 2-of-3 Safe, Matthew's liability proof | decision set supplied; named approval and ABI freeze pending |
| P0 | Matthew | `quoteSell`/guarded-sell math with proceeds rounded down; collateral, winning/VOID reserves, 10 ACON bond separation, and creator-surplus invariants; review payout code. | M4 decision set and bounded LMSR | planned; not implemented |
| P0 | Benny | One-market-per-fixture lifecycle, guarded sell, immutable YES/NO/VOID proposal, challenge bond, Safe-owned resolver registry/VRF v2.5/votes, finalization/VOID, single-use claims; publish exact ABI, Sepolia deployment/transaction smoke, Foundry evidence. | Named approval, exact ABI table, Matthew's accounting proof | planned; not implemented |
| P0 | Yudhveer | Required deterministic mock/manual JSON fixture and result catalog, EOA registration request and mock worker, separate narrow registrar/proposer keys, audit/rotation, M4 projections/API/history/portfolio/replay. Optional PandaScore only with written permission. | Team review of PR #30; exact role/event ABI and deployment handoff for chain writes and projections | PR #30 fixture catalog ready for review; draft #31 off-chain request/worker; draft #32 result assessments; no M4 chain write yet |
| P0 | Adriel | Multi-market fixture browsing/creation, guarded sell, portfolio, challenge, resolver vote, finalization/VOID and claim UI, wallet/freshness/error/component tests; Vercel deployment if hosting stretch lands. | Exact ABI, API/manifest, registered fixtures | planned; not implemented |
| P0 | Team | Automated Anvil normal/disputed/timeout/VOID/claim paths, Sepolia contract deployment/transaction smoke, indexed API equality, docs, and rehearsal; full public cross-layer flow if stretch target lands. | Integrated subsystem PRs and funded eligible resolver addresses | planned; no M4 integration run yet |

**Documentation on every code PR:** each owner updates the affected README, interface/API/deployment handoff, tests, and runbook. Update current-state architecture and top-level README only when the corresponding path is implemented and verified. The planning PR should reconcile target-design docs and M5 timing after team decisions, without changing M3 implementation claims.
