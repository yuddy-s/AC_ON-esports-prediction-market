# Backend Deployment Runbook

This runbook covers the Milestone 3 FastAPI service, PostgreSQL projections, and the single event-indexer worker. Ethereum contracts remain authoritative.

## Required handoff

Record the deployed source commit, chain ID, checksummed market/token addresses, deployment transaction and block, generated ABI path/version, enum order, confirmation depth, and example market/trade transactions. Never commit RPC credentials, database credentials, or private keys.

## Supabase

1. Take a schema backup or snapshot before applying migrations.
2. Set `DATABASE_URL` with the SQLAlchemy psycopg scheme and required SSL parameters.
3. Run `alembic upgrade head` once from a controlled release process.
4. Verify the Alembic revision and that indexer tables are empty or contain the expected registered deployment.
5. Roll back application code before attempting a schema downgrade; the initial projection schema is reproducibly rebuildable from chain events.

## Render

Deploy two processes from the same commit:

- Web service: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Single background worker: `python -m app.indexer.worker`

Configure `DATABASE_URL`, `FRONTEND_ORIGIN`, `SEPOLIA_RPC_URL`, `PREDICTION_MARKET_ADDRESS`, `PREDICTION_MARKET_DEPLOYMENT_BLOCK`, `PREDICTION_MARKET_ABI_PATH`, and the documented `INDEXER_*` settings. Upload or package the ABI from the exact deployed build. Run exactly one worker instance during Milestone 3 to avoid concurrent checkpoint writers.

## Verification and recovery

1. Check `/health` and `/api/indexer/status` before enabling frontend traffic.
2. Run `python -m app.indexer.worker --once`; startup must confirm the RPC chain ID before any checkpoint work. Then verify observed head, safe checkpoint, and lag.
3. Compare one indexed market/trade with its Sepolia transaction and event log.
4. Restart the worker and verify it resumes from the stored checkpoint without duplicates.
5. Use `python -m app.indexer.worker --rebuild` only during a maintenance window. It deletes derived projections for the configured contract and replays canonical events; it never writes to Ethereum.
6. If RPC or database connectivity fails, stop the worker, preserve PostgreSQL, correct configuration, and resume. Do not manually advance checkpoints.
