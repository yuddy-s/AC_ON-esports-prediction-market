# AC_ON Developer Guide

Status: Milestone 5 draft. Local implementation and deployment configuration are complete; public
Render/Vercel URLs and hosted acceptance evidence remain pending.

## Architecture And Trust Boundaries

Ethereum Sepolia contracts are authoritative for fixture registration, markets, positions, resolver
selection, settlement, and payouts. FastAPI and PostgreSQL provide reviewed source workflows and
derived reads. The indexer waits for two confirmations and can rebuild only chain-derived rows.
Registrar and proposer are separate least-privilege processes and accounts. PandaScore is
informational and must pass the independent [evidence review checklist](agent/EVIDENCE_REVIEW_CHECKLIST.md).

The public deployment is defined by `deployments/sepolia-2026-11-02/manifest.post-setup.json` and its
versioned ABI. Never pair its contract address with another ABI or deployment block.

## Codebase

- `contracts/`: Solidity, Foundry tests, deployment and Anvil journeys.
- `backend/app/`: API, source/review workflows, indexer, gateways, and workers.
- `backend/migrations/`: append-only Alembic revisions through `20261102_0008`.
- `backend/scripts/`: operator import/review, handoff validation, and smoke commands.
- `frontend/src/`: React UI, wallet writes, contract reads, and indexed history.
- `deployments/`: public manifests, versioned ABIs, receipts, and sanitized evidence.

## Local Setup

1. Copy the backend and frontend environment examples to their ignored local files.
2. From `backend/`, create a virtual environment and install `requirements.txt`.
3. Run `alembic current`; review the target database before `alembic upgrade head`.
4. From `frontend/`, run `npm ci`.
5. Start FastAPI, exactly one indexer, the frontend, and—only when intended—the registrar and
   proposer using the M4 application runbook.

Never print secrets during diagnostics. Safe-owner, resolver, creator, trader, and challenger keys
do not belong in service configuration. Browser variables contain public values only.

## Verification

```text
backend:  pytest
frontend: npm test; npm run typecheck; npm run build
contracts: forge fmt --check; forge build; forge test
public:   python -m scripts.smoke_public --api-base-url URL --frontend-url URL --manifest ../deployments/sepolia-2026-11-02/manifest.post-setup.json
```

GitHub Actions additionally runs a disposable PostgreSQL 16 job for migrations, uint256 precision,
replay, rebuild preservation, and reorganization behavior. Existing SQLite tests remain the fast
unit path. Foundry CI also runs ABI/source/runtime checks, pricing vectors, six Anvil journeys,
Slither, coverage, and secret scanning.

## Render And Supabase Deployment

The root `render.yaml` defines one free API and three smallest-plan paid workers. Automatic deploys
are off. The initial Blueprint sync can start billing for paid instances, but each worker starts in
a dormant state because its `*_WORKER_ENABLED` value is `false`. Services deploy from the repository
root so the indexer can read the frozen ABI under `deployments/`; their commands explicitly enter
`backend/`.

1. Record Supabase revision and pre-deployment counts; back it up outside Git.
2. Apply migrations from one controlled release process. Expected head is `20261102_0008`.
3. Create the Blueprint and enter every `sync: false` value in Render.
4. Deploy the API and confirm `/health`.
5. Set `INDEXER_WORKER_ENABLED=true`, manually deploy exactly one indexer, and wait for
   `/api/v2/indexer/status` to become current.
6. Set `REGISTRAR_WORKER_ENABLED=true` and `PROPOSER_WORKER_ENABLED=true`, then manually deploy the
   signer workers only after confirming their roles, balances, and expected pending work.
7. Configure the exact Vercel origin as `FRONTEND_ORIGIN` and run the public smoke command.
8. After evidence capture, suspend proposer and registrar, then the indexer. Set all three enable
   flags back to `false` before any later deployment and confirm suspension in Render billing; leave
   the free API available.

The registrar environment receives only `REGISTRAR_PRIVATE_KEY`; the proposer receives only
`PROPOSER_PRIVATE_KEY`. PandaScore import remains an operator action and its token is not required by
these four services.

## Monitoring And Recovery

- `/health` checks API/database availability.
- `/api/v2/indexer/status` must match chain, contract, deployment block, ABI, safe block, and recent
  update time. A small lag with an old timestamp is stale.
- On indexer failure, suspend duplicates, retain one worker, verify configuration, then resume.
- On signer uncertainty, check receipt, nonce, and contract state before retrying.
- Rebuild only chain-derived fixtures, markets, events, positions, and checkpoints. Preserve source,
  review, registration, assessment, intent, attempt, and audit records.
- During provider failure, retain the last observation and stop new proposal work.
- On key compromise, stop the worker, revoke the role through the Safe, grant/fund a replacement,
  reconcile pending state, update the managed secret, and restart.
- Never reset/drop the shared database or downgrade it as routine recovery.

## Contributing And Evidence

Branch from `dev`, keep changes scoped, add regression tests, and open a PR back to `dev`. Do not
change the frozen ABI, public APIs, or database meaning without cross-layer review. Every M5 PR
updates affected setup/recovery instructions, the integration matrix, and any defect entry.

Evidence must distinguish CI, local Anvil, public Sepolia, hosted services, and manual browser work.
Store only public URLs, transaction hashes, blocks, sanitized screenshots, and generated summaries;
never store credentials, raw signatures, or secret-bearing logs.
