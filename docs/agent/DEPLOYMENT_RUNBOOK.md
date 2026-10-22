# Backend Deployment Runbook

This runbook covers the Milestone 3 FastAPI service, PostgreSQL projections, and the single event-indexer worker. Ethereum contracts remain authoritative.

## Required handoff

Record the deployed source commit, chain ID, checksummed market/token addresses, deployment transaction and block, generated ABI path/version, enum order, confirmation depth, and example market/trade transactions. Never commit RPC credentials, database credentials, or private keys.

The completed [`deployments/sepolia-m3.json`](../../deployments/sepolia-m3.json) and exact-build ABIs are available under the [versioned handoff convention](../../deployments/README.md). They describe deployed source `6e30d516669e51d7f3e4bff0d8670168da9b1f83`, both contracts, market `0`, and the confirmed guarded-buy transaction. The manifest passes `python -m scripts.validate_handoff ../deployments/sepolia-m3.json` from `backend/`. The separate `sepolia-m3.template.json` remains unfilled for future deployments. A different ABI filename or deployment block for an already registered contract causes worker startup/sync to fail rather than silently reusing its checkpoint.

### Current M3 public configuration

For a worker launched from `backend/`, use:

```dotenv
INDEXER_CHAIN_ID=11155111
PREDICTION_MARKET_ADDRESS=0x19EF739001038Ce9DFB1E12Cf45A10c9250A60a7
PREDICTION_MARKET_DEPLOYMENT_BLOCK=11963761
PREDICTION_MARKET_ABI_PATH=../deployments/abi/PredictionMarket.6e30d516669e.792fa9f230ed.abi.json
INDEXER_CONFIRMATION_DEPTH=2
```

ACON is `0x315FCA0DDAA367446f36A3184D8f6b2Df76b5618`; the frontend needs that token address and its versioned ABI for faucet/approval. Configure RPC/database values privately. These are the final deployed addresses; earlier simulation addresses are superseded. See the [deployment/trade record](../../contracts/deployments/sepolia-m3-2026-10-21/README.md) for receipts and gas-estimation recovery.

Live contract state and RPC/ABI event decoding have passed verification. The complete frontend/indexer/API path also passed locally on Anvil. Hosted Sepolia database/indexer/API operation and deployed-frontend acceptance are still pending; use MetaMask for Sepolia writes because Coinbase Smart Wallet does not support sending transactions on that network.

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

At the previously recorded Supabase check on 2026-10-21, the configured database was at revision `20261018_0001`. The five indexer tables existed with zero rows, and the three preexisting sample-match rows remained. A local pre-migration export was reported saved outside Git. This is historical schema-setup evidence; recheck the target database before starting its worker. The contract smoke test did not verify hosted database contents.

## Render

Deploy two processes from the same commit:

- Web service: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Single background worker: `python -m app.indexer.worker`

Configure `DATABASE_URL`, `FRONTEND_ORIGIN`, `SEPOLIA_RPC_URL`, `PREDICTION_MARKET_ADDRESS`, `PREDICTION_MARKET_DEPLOYMENT_BLOCK`, `PREDICTION_MARKET_ABI_PATH`, and the documented `INDEXER_*` settings. Upload or package the ABI from the exact deployed build. Run exactly one worker instance during Milestone 3 to avoid concurrent checkpoint writers.

Set `DATABASE_URL` and `FRONTEND_ORIGIN` on the web service. Set the same `DATABASE_URL`, plus `SEPOLIA_RPC_URL` and the public M3 values above, on the worker. The API reads the active contract/checkpoint registered by the worker in that shared database. The manifest ABI path is repository-relative; if the worker command runs from `backend/`, set `PREDICTION_MARKET_ABI_PATH=../<manifest market.abi_path>` and verify it resolves inside the deployed filesystem. Set `FRONTEND_ORIGIN` to Adriel's deployed Vercel origin after it is known. Keep private values in Render environment settings. Deploy both processes from the same Git commit containing the published handoff and run migrations before starting the worker.

## Verification and recovery

1. Check `/health` and `/api/indexer/status` before enabling frontend traffic. The status `updated_at` timestamp should advance with worker polls; a small `lag_blocks` value with an old timestamp indicates a stalled worker.
2. Run `python -m app.indexer.worker --once`; startup must confirm the RPC chain ID before any checkpoint work. Then verify observed head, safe checkpoint, and lag.
3. Compare one indexed market/trade with its Sepolia transaction and event log. Query `/api/trades/by-transaction/{transaction_hash}` for the successful buy and verify the indexed trade appears after the safe checkpoint reaches the receipt block.
   From `backend/`, run `python -m scripts.smoke_sepolia --manifest ../deployments/sepolia-m3.json --api-base-url <API_URL>` with `SEPOLIA_RPC_URL` set privately. It also verifies that `PredictionMarket.paymentToken()` equals the manifest's ACON token address, without writing to Ethereum.
4. Restart the worker and verify it resumes from the stored checkpoint without duplicates.
5. Use `python -m app.indexer.worker --rebuild` only during a maintenance window. It deletes derived projections for the configured contract and replays canonical events; it never writes to Ethereum.
6. If RPC or database connectivity fails, stop the worker, preserve PostgreSQL, correct configuration, and resume. Do not manually advance checkpoints.

For the published example, the trade is `0xe5f5ff239ff3939cfc34c1c7719f2b1db9ef83d75f77f501236d004cb2d10c16`, block `11964663`, log index `104`. After the safe checkpoint reaches that block, `/api/trades/by-transaction/0xe5f5ff239ff3939cfc34c1c7719f2b1db9ef83d75f77f501236d004cb2d10c16` should include exactly one matching log: market `0`, outcome `0` (YES), shares `10000000000000000000`, and cost `5249584441082326050` ACON base units.

Market `0` accepts new buys only before **2026-10-28 17:01:12 UTC**. The recorded creation/trade events can still be backfilled and checked afterward, but a new wallet-trading demo will need a new funded market and updated example transaction references.
