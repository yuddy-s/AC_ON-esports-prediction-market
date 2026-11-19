# AC_ON Developer Guide

Status: Milestone 5 draft. The Vercel frontend and free Render API are public. Supabase and Sepolia
are persistent public dependencies; the indexer, registrar, proposer, and PandaScore tools are
operator-run locally during controlled integration windows.

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
public:   python -m scripts.smoke_public --api-base-url URL --frontend-url URL --manifest ../deployments/sepolia-2026-11-02/manifest.post-setup.json --max-indexer-age-seconds 120 --max-indexer-lag-blocks 20
```

GitHub Actions additionally runs a disposable PostgreSQL 16 job for migrations, uint256 precision,
replay, rebuild preservation, and reorganization behavior. Existing SQLite tests remain the fast
unit path. Foundry CI also runs ABI/source/runtime checks, pricing vectors, six Anvil journeys,
Slither, coverage, and secret scanning.

## Hybrid Render, Supabase, And Local-Worker Deployment

The deployed M5 topology uses the public Vercel frontend at
`https://acon-esports-market.vercel.app`, the free Render API at
`https://ac-on-esports-prediction-market.onrender.com`, Supabase PostgreSQL, and the Sepolia M4
contracts. The root `render.yaml` documents an optional paid-worker topology; it is not the topology
currently deployed. Do not sync that Blueprint when the intent is to use only the free API.

1. Rotate any exposed credential, back up Supabase, and record revision/table counts. Expected head
   is `20261102_0008`.
2. Create a free Render web service from `dev`, leave the root directory unset, build with
   `pip install -r backend/requirements.txt`, and start with
   `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Give the API only `DATABASE_URL`, exact `FRONTEND_ORIGIN`, and explicit
   `INDEXER_CHAIN_ID=11155111`. Never give it RPC/provider credentials or private keys.
4. Confirm `/health`, then run exactly one local indexer from `backend/` with
   `python -m app.indexer.worker`. Use `--once` for a catch-up pass or leave it polling during a
   demonstration. The API reads the resulting Supabase projections without a restart.
5. Inspect expected jobs before running `python -m app.registrar_process` or
   `python -m app.proposer_process`. Each uses its separate local signer account; stop it after the
   intended job is confirmed. `--once` performs one controlled processing pass.
6. Run PandaScore import/review commands only from the private operator environment.
7. While the local indexer is current, run the public smoke command and record sanitized evidence.

The laptop must remain awake while a continuously polling local worker is needed. When it stops,
the frontend and API remain public but indexed projections become stale. Evidence and presentation
material must call these processes `local operator-run workers`, not hosted Render workers.

## Monitoring And Recovery

- `/health` checks API/database availability.
- `/api/v2/indexer/status` must match chain, contract, deployment block, ABI, safe block, and recent
  update time. A small lag with an old timestamp is stale.
- On indexer failure, stop duplicate local processes, retain one worker, verify configuration, then
  resume from the stored checkpoint.
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
