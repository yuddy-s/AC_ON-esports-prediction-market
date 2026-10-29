# AC_ON Agent Notes

AC_ON is a testnet-only decentralized esports prediction market. Users connect a wallet and trade YES/NO shares on binary esports match outcomes. The intended system uses on-chain contracts for market state, trading, challenges, resolver voting, settlement, and payouts; off-chain services support esports data, oracle proposals, indexing, and API/database reads.

This folder is shared working context for coding agents and human developers. It is not the official course artifact bundle unless the team explicitly decides to reuse parts of it.

Keep this folder small. It should help agents pick the right slice of work without becoming a second project report.

## Files

- `ARCHITECTURE.md`: current repo state, target architecture, known gaps, and setup notes.
- `TASKS.md`: current team assignments and coding-agent work queue.
- [`milestones/MILESTONE_4.md`](milestones/MILESTONE_4.md): proposed feature-complete M4 ownership, dependencies, one-week sequence, and full test plan.
- [`interfaces/M4_FEATURE_COMPLETE_INTERFACE.md`](interfaces/M4_FEATURE_COMPLETE_INTERFACE.md): supplied M4 fixture/trading/lifecycle/resolver decision set; approving names and exact ABI types still need PR review, and **no M4 feature is implemented**.
- `APPLICATION_ROADMAP.md`: canonical product checklist, blockers, ABI handoff, and remaining work by owner.
- `DEPLOYMENT_RUNBOOK.md`: Supabase migrations plus Render API/indexer-worker deployment and recovery steps.
- [`../../deployments/README.md`](../../deployments/README.md): public Sepolia handoff and versioned ABI convention.
- [`../../deployments/sepolia-m3.json`](../../deployments/sepolia-m3.json): completed M3 deployment manifest with exact-build ABIs and confirmed creation/trade examples.
- [`../../contracts/deployments/sepolia-m3-2026-10-21/README.md`](../../contracts/deployments/sepolia-m3-2026-10-21/README.md): deployment recovery, verified live buy, demo deadline, and remaining hosted integration work.
- `interfaces/`: proposed or approved cross-layer interface decision records.
- `milestones/`: milestone scope so agents do not overbuild beyond the active course milestone.

## Agent Workflow

1. Read `docs/agent/README.md`.
2. Read `ARCHITECTURE.md`.
3. Read `APPLICATION_ROADMAP.md` for the current implementation state and blockers.
4. Check `TASKS.md`.
5. Check the active milestone file in `milestones/`.
6. Read any relevant decision record in `interfaces/`.
7. Inspect the relevant code before editing.
8. Make scoped changes on a branch.
9. Run applicable tests or document why they could not run.
10. Update these docs only when the change affects architecture, setup, milestone scope, or task ownership.

## Branch Workflow

The team should keep `main` stable and use `dev` as the integration branch.

- `main`: stable branch for instructor-facing snapshots, releases, and known-good demos.
- `dev`: shared integration branch for completed work before promotion to `main`.
- feature branches: short-lived branches for each scoped task.

Recommended flow:

1. Start from the latest `dev`.
2. Create a branch with a clear name, for example `feature/frontend-contract-read`, `backend/api-scaffold`, or `docs/milestone-2-plan`.
3. Keep the branch focused on one subsystem or task.
4. Run relevant checks before opening a pull request.
5. Merge into `dev` first.
6. Promote `dev` to `main` only after the integrated app is in a demo-ready state.

Agents should not commit directly to `main`. Agents should avoid direct commits to `dev` unless the team explicitly asks for that. If a change touches multiple subsystems, update `ARCHITECTURE.md` and `TASKS.md`.

## Course Artifacts

Course artifacts such as presentation slides, formal design documents, UML diagrams, written reports, and final submission materials are separate team deliverables. These agent docs can inform those artifacts, but they should not replace them unless the team chooses to store official artifacts in the repository.
