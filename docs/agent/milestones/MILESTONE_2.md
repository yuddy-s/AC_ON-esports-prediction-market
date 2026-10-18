# Milestone 2: Design and Setup

Status: active

## Course Goal

Presentation should cover system architecture, architecture reasoning, tech stack choices, and a demo of whatever is running so far.

Artifacts are maintained separately by the team, but this repository should support them with accurate implementation docs, a CI skeleton, and a minimal working prototype.

## Repository Scope For This Milestone

Milestone 2 should prove the architecture is viable. Prefer vertical integration over polished feature depth.

Target demo:

- frontend can connect a wallet
- frontend can read at least one contract value
- frontend can execute at least one contract write
- one sample market can exist
- simple YES/NO trading path exists, or a temporary trade stub is clearly documented
- backend can run locally
- backend can connect to PostgreSQL or a clearly documented temporary development database
- oracle/backend architecture is scaffolded
- contract events can be observed or indexed in a basic form
- setup steps are documented
- CI skeleton exists

## Current Milestone 2 State

Implemented:

- frontend app
- wallet connect
- address display
- balance display
- FastAPI backend scaffold
- Supabase PostgreSQL sample-data path
- fake sample-match endpoints

Missing:

- contracts
- contract read
- contract write
- sample market
- oracle scaffold
- indexer scaffold
- contract events
- full cross-subsystem setup docs

## Team Artifact Assignments

| Owner | Assignment |
|---|---|
| Adriel | Team roles, Section 4 frontend row, Section 6 prototype, README, submit. |
| Benny | Section 2 class diagram + market state diagram, Section 4 contracts row, CI pipeline. |
| Matthew | Section 3 LMSR + liquidity funding rows, Section 2 trade sequence diagram, renumber requirements FR-01/NFR-01, claim-winnings story. |
| Yudhveer | Section 1 architecture diagram with on/off-chain labels, oracle and resolver separate, Section 2 resolution sequence diagram, Section 3 trust model, Section 4 backend/DB rows, branch protection. |

## Prioritized Task List

1. Create/confirm `dev` branch and branch workflow.
2. Add CI skeleton for frontend build/lint.
3. Add minimal Foundry contract scaffold.
4. Implement one minimal sample market contract.
5. Emit at least one event from contract state change.
6. Wire frontend to read one contract value.
7. Wire frontend to perform one contract write.
8. Add minimal FastAPI backend with `GET /health`.
9. Choose and document Milestone 2 database mode.
10. Add a small oracle/indexer scaffold or documented boundary. The real indexer is deferred for now.
11. Update setup docs with commands that actually work.
12. Prepare demo checklist for the presentation.

## Demo Checklist

- Start frontend.
- Connect Coinbase Wallet.
- Show connected address and balance.
- Show contract read.
- Execute contract write.
- Show transaction or resulting state change.
- Start backend.
- Hit backend health endpoint.
- Explain planned oracle/indexer/database boundary.

## Out Of Scope For Milestone 2 Unless Already Implemented

- Full LMSR pricing.
- Full resolver governance.
- Production oracle integrations.
- Complete challenge/resolution flow.
- Mainnet deployment.
- Visual polish beyond basic usability.
