# Backend Deployment Runbook

> Current M4 local/Sepolia operations are documented in
> [M4_APPLICATION_RUNBOOK.md](M4_APPLICATION_RUNBOOK.md). This file retains historical
> M3 deployment and recovery context; do not copy its M3 addresses into M4 configuration.

This runbook documents the deployed M3 API, PostgreSQL projections, and single indexer worker; M4 contract deployment and service integration are not yet operational. Ethereum contracts remain authoritative.

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

The deployed M3 contract/RPC/ABI path and local Anvil cross-layer demo have passed verification. Merged PRs #37/#38 provide locally verified M4 contract/economics artifacts and exact ABI, but no M4 Sepolia deployment, Safe/VRF ownership, registrar/proposer role grants, or cross-layer M4 smoke is recorded. Hosted M3 worker/API and frontend acceptance remain pending; use MetaMask for Sepolia writes because Coinbase Smart Wallet does not support transactions on that network.

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

At the previously recorded Supabase check on 2026-10-21, the configured database was at revision `20261018_0001`. The five indexer tables existed with zero rows, and the three preexisting sample-match rows remained. A local pre-migration export was reported saved outside Git. On 2026-10-22, a single locally run Sepolia worker populated that database with one market and two trades; local FastAPI returned the recorded buy, and `smoke_sepolia` passed against that API. This verifies the database projections, not persistent Render worker/API operation or a deployed-frontend buy. Recheck the database and whether a worker is already running before starting another one.

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

## Historical M4 integration notes

The deployment/gateway warnings below describe the earlier implementation baseline and
are retained for audit context. The real gateways, role grants, M4 deployment, and initial
live registration/market/trade smoke are now complete; use
[M4_APPLICATION_RUNBOOK.md](M4_APPLICATION_RUNBOOK.md) for current commands and status.

### Proposed PandaScore source process

PR #39 merged the server-only PandaScore adapter. PandaScore remains optional under the approved M4 design. Before any live call, the team must choose to enable it and configure `PANDASCORE_USE_APPROVED=true` and `PANDASCORE_API_TOKEN` only in the operator process's secret environment. Run `python -m scripts.import_pandascore all --validate-only` from `backend/` to inspect normalized counts, then run without `--validate-only` against the intended database. Check `DATABASE_URL` first. Do not place the token in a URL, frontend variable, log, or repository file. A rate-limit, access-denied, or malformed-response failure stops the import; preserve existing source rows and retry in a later operator window. A PandaScore result needs a separate operator review tied to that exact observation before the oracle may create an intent. This process does not replace the single indexer worker or register/create a market.

Apply migration `20261101_0006` before provider import. A selected fixture requires an operator review with separate organizer evidence: `python -m scripts.review_fixture <catalog-id> --reviewer <operator-id> --approve --evidence-url <organizer-url> --evidence-hash <0x-sha256>`. Fixture and result reviews reject `pandascore.co` and every `*.pandascore.co` hostname; the operator must verify that another URL is genuinely independent. `--revoke` removes current approval. Review events survive indexer rebuilds. Reapprove if team IDs/order or scheduled start change. An off-chain approval permits a player to request registrar action but does not make the fixture registered on-chain. Do not run this operator command through a public API.

Apply migration `20261102_0008` before starting the M4 workers. After checking an organizer's result, run `python -m scripts.review_result <observation-id> --reviewer <operator-id> --approve --evidence-url <organizer-url> --evidence-hash <0x-sha256>`; use `--revoke` for a later rejection. A new or corrected observation needs its own review. These events survive indexer rebuilds. An approved review only permits intent planning; the proposer process still requires the merged ABI, narrow role, verified closed market, and confirmed chain read.

PRs #30-#34 and #39 merged the fixture, registration, assessment, audit, and source-review migrations through `20261101_0007`. Before migrating any database, check its current Alembic revision and whether these revisions have already been applied. Back up the target and use one approved migration process. Verify that imported source and signer-audit tables survive any later indexer rebuild. Never point a local importer at a hosted database by accident.

The registration worker currently has only a mock gateway. Its `awaiting_abi` jobs cannot be activated for a real chain. The operator must verify the merged compiled M4 ABI, deployment manifest, chain ID, deployment block, registrar role grant, and separate registrar key. The production gateway must read the contract and require the configured confirmation depth before reporting `confirmed`. It may retry only a failure known to precede submission; `submission_unknown` requires manual receipt/nonce and contract-state reconciliation before any resend. Preserve the job-event audit rows and never delete them during an indexer rebuild.

The oracle worker likewise has only a mock gateway. It may plan an intent only for a chain-verified closed, unproposed market linked to a curated fixture and latest assessed result. Its separate signer must not start until the deployed contract, proposal call, market linkage, role grant, and key are verified. `correction_review` and `submission_unknown` require manual evidence/chain reconciliation; never silently edit an immutable intent or resubmit an uncertain transaction. The append-only assessment, intent, and attempt tables are operational records, not chain projections.

The merged registration recovery migration (`20261030_0005`) stores a fixture snapshot, authorizing wallet, challenge ID, and nonce/message hashes on each new audit event. Earlier events remain attributable even after challenge cleanup; pre-migration event metadata remains null rather than guessing from the mutable job. A fresh signed request may reuse a terminal job only for the explicitly recoverable failure codes documented in `backend/README.md`; retain prior events and hashes. Do not reset a submitted, uncertain, confirmed, or chain-conflicting job. Verify fixture Team A/B IDs and start time remain consistent with confirmed registration before importing changed source data. The importer rejects frozen-field changes rather than silently altering the oracle's team mapping.

Run exactly one indexer worker process. The registrar and proposer are separate processes with separate narrow role keys; no key belongs in Git, frontend variables, or logs. Keep local keys in ignored environment files and hosted keys in service secrets. On suspected compromise, stop the affected signer, revoke its role via the Safe, grant a replacement account, reconcile pending transactions, and restart only after recording the rotation in the private operator log. The proposal service must likewise reconcile chain state before retrying and must not expose a public arbitrary-outcome signing endpoint. Configure an edge rate limit for registration POST routes before public exposure; per-wallet limits do not stop requests from many fresh addresses.

When M4 indexing is implemented, compare `/api/v2/indexer/status` `chain_id`, `contract_address`, `abi_version`, safe block, and `updated_at` with the published M4 deployment handoff before enabling M4 indexed reads. A fixture's `registration_request_status` is an off-chain job field; only a gateway-confirmed on-chain registration may permit the separate user-signed market creation action.
