# Tasks

Use this file to coordinate current work. Official course artifacts may live outside the repo, but this list records who owns each slice so agents do not duplicate or drift.

## Course Artifact Assignments

| Owner | Area | Assignment | Repo Impact | Status |
|---|---|---|---|---|
| Adriel | coordination/frontend | Team roles, Section 4 frontend row, Section 6 prototype, README, submit | Keep top-level README and frontend prototype notes accurate. | assigned |
| Benny | diagrams/contracts/CI | Section 2 class diagram + market state diagram, Section 4 contracts row, CI pipeline | Add CI skeleton and keep contract architecture notes current. | assigned |
| Matthew | LMSR/requirements | Section 3 LMSR + liquidity funding rows, Section 2 trade sequence diagram, renumber requirements FR-01/NFR-01, claim-winnings story | Keep LMSR/trading assumptions aligned with future contract work. | assigned |
| Yudhveer | architecture/backend/trust | Section 1 architecture diagram with on/off-chain labels, oracle and resolver separation, Section 2 resolution sequence diagram, Section 3 trust model, Section 4 backend/DB rows, branch protection | Keep architecture/trust/backend notes aligned with implementation. | assigned |

## Milestone 2 Coding Queue

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

## Done

| Owner | Subsystem | Task | Status |
|---|---|---|---|
| team | frontend | Minimal wallet connect prototype with address and balance display. | done |
| team | docs | Initial agent planning docs and milestone structure. | done |

## Product Ownership: Milestones 3-6

These ownership areas remain stable through the final product so later milestones extend existing work instead of redistributing subsystems.

| Owner | Primary product ownership | Testing and deployment ownership |
|---|---|---|
| Adriel | Frontend and Web3 flows: browse/create markets, quote/trade, positions, challenges, resolver voting, claims, and transaction/indexer synchronization. | Vitest and frontend end-to-end coverage; Vercel deployment. |
| Benny | Solidity market lifecycle and authorization, resolver registry/selection/voting, settlement, claims, VOID behavior, contract events, and Sepolia deployment scripts. | Foundry unit/security tests, contract static analysis, and contract CI. |
| Matthew | `LMSR.sol`, 1e18 fixed-point arithmetic, `b = 50`, creator subsidy, buy/sell pricing, and payout/VOID accounting rules. Trading/platform fees are out of scope. | Foundry fuzz/invariant tests and economic/accounting documentation. |
| Yudhveer | FastAPI, PostgreSQL, event indexer, oracle providers/signer operations, resolver projections/APIs, replay/reorganization recovery, and trust/security documentation. | Pytest and cross-layer integration coverage; Render/Supabase deployment. |
| Team | ABI/event freezes, secrets policy, live demos, cross-layer acceptance, reports, and release validation. | Review required across subsystem boundaries. |

## Milestone 3 MVP Queue

The shared priority is one end-to-end guarded buy on Ethereum Sepolia. Full resolver committee implementation is deferred until that slice works and the protocol rules are approved.

The approved cross-layer freeze is documented in [`interfaces/M3_TRADING_INTERFACE.md`](interfaces/M3_TRADING_INTERFACE.md). Dependent contract, indexer, and frontend work must implement that interface or update the decision record through team review.

| Priority | Owner | Subsystem | Task | Dependencies | Status |
|---|---|---|---|---|---|
| P0 | team | interfaces | Freeze the payment asset, market/trade ABI, enum order, event fields, numeric units, and deployment handoff. | Team approval of the decision record | approved in PR #12 |
| P0 | Matthew | LMSR/contracts | Implement `LMSR.sol` with 1e18 precision, `b = 50`, creator subsidy `ceil(b * ln(2))`, quote/cost math, and economic invariants. | team review | merged in PR #13 |
| P0 | Benny | contracts | Integrate ACON subsidy collection, LMSR quotes, guarded YES/NO buy, positions, and `TradeExecuted`. | interface freeze and LMSR library | implemented in 4c57dc0 on feature/guarded-buy; review/ABI handoff and fresh Sepolia deployment pending |
| P0 | Yudhveer | indexer/database | Implement migrations, unique event identity, atomic checkpoints, confirmation handling, deterministic rebuild, and reorg recovery. | final live validation waits on deployment | merged in PR #10 |
| P0 | Yudhveer | backend | Implement paginated indexed market/trade/status read APIs with derived-state metadata. | indexed schema | merged in PR #10 |
| P0 | Yudhveer | RPC worker | Implement validated JSON-RPC retrieval, bounded polling/retries/range splitting, ABI decoder boundary, clean shutdown, and deployment runbook. | live validation waits on exact ABI and deployment record | merged in PR #15; live M3 validation pending |
| P0 | Adriel | frontend | Implement quote/buy and submitted/mined/indexed UI states. | ABI and backend endpoints | contract ABI available for review; new addresses and live integration pending |
| P1 | team | integration | Deploy fresh Sepolia contract and run contract-to-indexer-to-API-to-frontend demo. | P0 slice | blocked |
| P1 | Yudhveer | oracle | Add provider and least-privilege signer boundaries with deterministic mock tests. | proposal/challenge ABI | blocked |
| P2 | Benny | resolver contracts | Implement authoritative eligibility, randomness, conflict checks, selection, voting, quorum, timeout, and finalization rules. | protocol decision and working trading slice | deferred to Milestone 4 |
| P2 | Yudhveer | resolver backend | Index resolver events and expose committee, vote, quorum, and timeout status without making authoritative decisions. | resolver event interface | deferred to Milestone 4 |
| P2 | team | CI/tests | Add cross-layer integration job or reproducible local integration harness. | working vertical slice | blocked |

Contract handoff/setup and current test coverage are documented in [`../../contracts/README.md`](../../contracts/README.md). The existing Sepolia address is the M2 prototype, not the new ACON/LMSR deployment.
