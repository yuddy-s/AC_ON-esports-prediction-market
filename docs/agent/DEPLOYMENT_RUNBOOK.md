# Backend Deployment Runbook

This runbook covers the Milestone 3 FastAPI service, PostgreSQL projections, and the single event-indexer worker. Ethereum contracts remain authoritative.

## Required handoff

Record the deployed source commit, chain ID, checksummed market/token addresses, deployment transaction and block, generated ABI path/version, enum order, confirmation depth, and example market/trade transactions. Never commit RPC credentials, database credentials, or private keys.

Use the [versioned ABI and manifest convention](../../deployments/README.md). The current `sepolia-m3.template.json` is intentionally unfilled. After Benny provides the exact deployment values and ABI files, validate the completed manifest from `backend/` with `python -m scripts.validate_handoff ../deployments/sepolia-m3.json`. A different ABI filename or deployment block for an already registered contract causes worker startup/sync to fail rather than silently reusing its checkpoint.

## Supabase

1. Take a schema backup or snapshot before applying migrations.
2. Set `DATABASE_URL` with the SQLAlchemy psycopg scheme and required SSL parameters.
3. Run `alembic upgrade head` once from a controlled release process.
4. Verify the Alembic revision and that indexer tables are empty or contain the expected registered deployment.
5. Roll back application code before attempting a schema downgrade; the initial projection schema is reproducibly rebuildable from chain events.

Read-only staging verification after migration (use the Supabase SQL editor or another approved SQL client):

```sql
SELECT version_num FROM alembic_version;
SELECT table_name FROM information_schema.tables
WHERE table_schema = current_schema()
  AND table_name IN ('indexed_contracts', 'indexer_checkpoints', 'processed_logs', 'markets', 'trades')
ORDER BY table_name;
SELECT count(*) AS registered_contracts FROM indexed_contracts;
SELECT count(*) AS projected_markets FROM markets;
SELECT count(*) AS projected_trades FROM trades;
```

The expected Alembic revision is `20261018_0001`. Before a worker runs, the three counts should be zero for a new database. Preserve any existing rows if this is not a fresh database.

As of 2026-10-21, the database configured by the local `backend/.env` is at revision `20261018_0001`. The five indexer tables exist and each has zero rows; the three preexisting sample-match rows remain. A local pre-migration export of those sample rows and table metadata was saved outside Git. This confirms schema setup only; no worker has indexed live Sepolia data there.

## Render

Deploy two processes from the same commit:

- Web service: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Single background worker: `python -m app.indexer.worker`

Configure `DATABASE_URL`, `FRONTEND_ORIGIN`, `SEPOLIA_RPC_URL`, `PREDICTION_MARKET_ADDRESS`, `PREDICTION_MARKET_DEPLOYMENT_BLOCK`, `PREDICTION_MARKET_ABI_PATH`, and the documented `INDEXER_*` settings. Upload or package the ABI from the exact deployed build. Run exactly one worker instance during Milestone 3 to avoid concurrent checkpoint writers.

Set `DATABASE_URL` and `FRONTEND_ORIGIN` on the web service. Set `DATABASE_URL`, `SEPOLIA_RPC_URL`, `INDEXER_CHAIN_ID=11155111`, the manifest's market address/deployment block, and the documented `INDEXER_*` values on the worker. The manifest ABI path is repository-relative; if the worker command runs from `backend/`, set `PREDICTION_MARKET_ABI_PATH=../<manifest market.abi_path>` and verify it resolves inside the deployed filesystem. Set `FRONTEND_ORIGIN` to Adriel's deployed Vercel origin after it is known. Keep all private values in Render environment settings, not in the public manifest. Deploy both processes from the same Git commit and run migrations before starting the worker.

## Verification and recovery

1. Check `/health` and `/api/indexer/status` before enabling frontend traffic. The status `updated_at` timestamp should advance with worker polls; a small `lag_blocks` value with an old timestamp indicates a stalled worker.
2. Run `python -m app.indexer.worker --once`; startup must confirm the RPC chain ID before any checkpoint work. Then verify observed head, safe checkpoint, and lag.
3. Compare one indexed market/trade with its Sepolia transaction and event log. Query `/api/trades/by-transaction/{transaction_hash}` for the successful buy and verify the indexed trade appears after the safe checkpoint reaches the receipt block.
   From `backend/`, run `python -m scripts.smoke_sepolia --manifest ../deployments/sepolia-m3.json --api-base-url <API_URL>` with `SEPOLIA_RPC_URL` set privately. This performs the same comparison without writing to Ethereum.
4. Restart the worker and verify it resumes from the stored checkpoint without duplicates.
5. Use `python -m app.indexer.worker --rebuild` only during a maintenance window. It deletes derived projections for the configured contract and replays canonical events; it never writes to Ethereum.
6. If RPC or database connectivity fails, stop the worker, preserve PostgreSQL, correct configuration, and resume. Do not manually advance checkpoints.
