# AC_ON Agent Notes

AC_ON is a testnet-only decentralized esports prediction market. Users connect a wallet and trade YES/NO shares on binary esports match outcomes. The intended system uses on-chain contracts for market state, trading, challenges, resolver voting, settlement, and payouts; off-chain services support esports data, oracle proposals, indexing, and API/database reads.

This folder is shared working context for coding agents and human developers. It is not the official course artifact bundle unless the team explicitly decides to reuse parts of it.

Keep this folder small. It should help agents pick the right slice of work without becoming a second project report.

## Files

- `ARCHITECTURE.md`: current repo state, target architecture, known gaps, and setup notes.
- `TASKS.md`: current team assignments and coding-agent work queue.
- `interfaces/`: proposed or approved cross-layer interface decision records.
- `milestones/`: milestone scope so agents do not overbuild beyond the active course milestone.

## Agent Workflow

1. Read `docs/agent/README.md`.
2. Read `ARCHITECTURE.md`.
3. Check `TASKS.md`.
4. Check the active milestone file in `milestones/`.
5. Read any relevant decision record in `interfaces/`.
6. Inspect the relevant code before editing.
7. Make scoped changes on a branch.
8. Run applicable tests or document why they could not run.
9. Update these docs only when the change affects architecture, setup, milestone scope, or task ownership.

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
