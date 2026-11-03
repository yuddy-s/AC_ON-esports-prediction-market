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

The M4 contract ABI and economic model are now available in merged PRs #37/#38. The deployed M3 contracts remain the live Sepolia baseline; use the M4 handoff for local Anvil work and do not treat the M4 source as deployed.

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
| P1 | team | integration | Run the contract-to-indexer-to-API-to-frontend demo against deployed M3 contracts. | hosted worker/API/frontend configuration | complete on local Anvil; hosted M3 Sepolia acceptance remains pending |
| P1 | Yudhveer | oracle | Add provider and least-privilege signer boundaries with deterministic mock tests. | proposal/challenge ABI | blocked |
| P2 | Benny | resolver contracts | Deploy and configure the merged M4 resolver implementation and validate the live VRF/role handoff. | M4 Safe, funded VRF subscription, eligible resolver pool | Contract implementation merged and locally verified in #37; fresh Sepolia deployment pending |
| P2 | Yudhveer | resolver backend | Index resolver events and expose committee, vote, quorum, and timeout status without making authoritative decisions. | Merged M4 ABI/event fixtures; deployment for live validation | Not implemented; part of remaining M4 indexer/API work |
| P2 | team | CI/tests | Add a cross-layer integration job or reproducible local integration harness. | working vertical slice | reproducible local flow documented and manually verified; automated cross-layer CI remains a follow-up |

Use the validated [`../../deployments/sepolia-m3.json`](../../deployments/sepolia-m3.json) for M3 addresses, blocks, versioned ABIs, and creation/trade transactions. The [deployment and live-buy evidence](../../contracts/deployments/sepolia-m3-2026-10-21/README.md) is published in PR #19. Market `0` stopped accepting trades on **2026-10-28 at 17:01:12 UTC**; use a newly funded market for any later trade demo. PR #20 updated the frontend to the M3 ABI and environment-driven addresses, including the six-output `getMarket` representation. Use MetaMask for Sepolia writes because Coinbase Smart Wallet does not support sending transactions on Ethereum Sepolia.

## Active Milestone 4 Feature-Complete Queue

Status: **M4 target approved; contract and economics implementation merged and locally verified.** Fresh deployment, Safe/VRF and role handoff, backend chain integration, frontend integration, and cross-layer acceptance remain.

For each owner, see [M4 Owner Handoffs And Roadblocks](milestones/MILESTONE_4.md#owner-handoffs-and-roadblocks) for what can start now, the specific artifact or access that blocks later work, and who must publish the handoff. A dependency below does not block the owner's independent preparation.

| Priority | Owner | Deliverable and acceptance evidence | Dependency | Status |
|---|---|---|---|---|
| P0 | Team | Complete the M4 deployment, Safe/VRF, and restricted service-role handoff using the merged ABI. | Fresh Sepolia deployment and funded VRF subscription; eligible resolver pool | ABI/economic proof merged in #37/#38; deployment and role handoff pending |
| P0 | Matthew | Buy/sell/payout rounding proof, collateral invariants, and accounting review. | Integrated Anvil lifecycle and claim journeys | Economic proof and stateful invariants merged in #38 and included with #37; cross-layer reconciliation remains |
| P0 | Benny | Deploy the merged lifecycle contract, transfer administration/VRF ownership to the Safe, grant narrow service roles, and publish deployment/transaction evidence. | Safe, funded VRF subscription, resolver pool, deployment credentials | Contract, exact ABI, local Foundry/Anvil and security evidence merged in #37; economics proof merged in #38; Sepolia handoff remains |
| P0 | Yudhveer | Validate the implemented registrar/proposer gateways and M4 projections/APIs against the fresh deployment; capture Anvil/Sepolia evidence. | Live writes need deployment, manifest, private configuration, and role grants | Current integration branch implements gateways, migration `20261102_0008`, `/api/v2`, replay-safe lifecycle/portfolio projections, and M4 frontend history wiring; live credentialed evidence remains pending. |
| P1 | Yudhveer | Add fixture registration-request status to catalog reads and active ABI version to indexer status; keep M3 routes compatible. | Contract deployment handoff | merged in PR #33; fixture-to-market and lifecycle/portfolio APIs still require M4 events |
| P1 | Yudhveer | Preserve signed fixture snapshots across recoverable registration retries; preserve result team mapping and confirmed-registration start time in source imports. | Production registrar integration | merged in PR #34; unknown submissions still require reconciliation before retry |
| P0 | Adriel | Complete and test M4 contract writes, resolution, resolver, claim, and portfolio UI. | Backend APIs and M4 deployment; registered fixtures | PR #40 contract actions and stacked PR #43 portfolio are open for review; full integration remains pending |
| P0 | Team | Run full local Anvil journeys, fresh Sepolia smoke, contract/indexer/API/UI reconciliation, and presentation rehearsal. | Integrated subsystems, Safe/roles, and eligible resolvers | Not yet verified end to end |

**Documentation on every code PR:** each owner updates the affected README, interface/API/deployment handoff, tests, and runbook. Update current-state architecture and top-level README only when the corresponding path is implemented and verified. The planning PR should reconcile target-design docs and M5 timing after team decisions, without changing M3 implementation claims.
