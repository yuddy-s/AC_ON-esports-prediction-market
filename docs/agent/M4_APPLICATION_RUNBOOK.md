# M4 full-application runbook

This is the current handoff for coding agents running AC_ON against the configured
Supabase database and the M4 Ethereum Sepolia deployment. Contracts are authoritative;
PostgreSQL and `/api/v2` are derived projections.

## Current deployment

- Chain: Ethereum Sepolia (`11155111`)
- PredictionMarket: `0x03ae48f03C7822540a91DA2168602bd49dC510E9`
- ACON test token: `0xf85b2278a810410c6AE0b7490d34671E0C8e6E90`
- Deployment block: `12051223`
- Frozen ABI: `deployments/abi/PredictionMarket.721a6fef039a.4af9297937eb.abi.json`
- ABI SHA-256: `4af9297937eb1b1b277a8c8d83e78ceb05c5db66cb120f1d39b80fdfc1015a91`
- Manifest: `deployments/sepolia-2026-11-02/manifest.post-setup.json`
- Database revision: `20261102_0008`

Do not use the historical M3 addresses or ABI for M4. Never print or commit RPC URLs,
database URLs, PandaScore tokens, private keys, or recovery phrases.

## One-time setup

From the repository root on Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic current
alembic upgrade head
```

`backend/.env` must remain Git-ignored. Start from `.env.example` and configure the
private database/RPC/provider/signing values locally. The working public M4 values are:

```dotenv
FRONTEND_ORIGIN=http://localhost:5173
INDEXER_CHAIN_ID=11155111
PREDICTION_MARKET_ADDRESS=0x03ae48f03C7822540a91DA2168602bd49dC510E9
PREDICTION_MARKET_DEPLOYMENT_BLOCK=12051223
PREDICTION_MARKET_ABI_PATH=../deployments/abi/PredictionMarket.721a6fef039a.4af9297937eb.abi.json
INDEXER_CONFIRMATION_DEPTH=2
INDEXER_BLOCK_BATCH_SIZE=10
```

The configured Alchemy Sepolia endpoint rejects the former 500-block `eth_getLogs`
batch. Keep the batch at 10 unless a different provider is verified. The API accepts
both `localhost:5173` and `127.0.0.1:5173` when either is the configured local origin.

Frontend configuration in `frontend/.env.local`:

```dotenv
VITE_CHAIN=sepolia
VITE_PREDICTION_MARKET_ADDRESS=0x03ae48f03C7822540a91DA2168602bd49dC510E9
VITE_ACON_TOKEN_ADDRESS=0xf85b2278a810410c6AE0b7490d34671E0C8e6E90
VITE_API_URL=http://127.0.0.1:8000
```

## Start the complete read application

Use three terminals. Run exactly one indexer.

```powershell
# Terminal 1
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2
cd backend
.\.venv\Scripts\python.exe -m app.indexer.worker

# Terminal 3
cd frontend
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/`. Health checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/v2/indexer/status
Invoke-RestMethod http://127.0.0.1:8000/api/v2/markets
```

A healthy two-confirmation indexer normally reports `lag_blocks: 2`. Its
`updated_at` must keep advancing. A mined wallet transaction is not indexed until the
safe block reaches its receipt block. If the UI says “indexer worker has not updated,”
run `python -m app.indexer.worker --once` or start the continuous worker; do not alter
the checkpoint manually.

## Signer workers

Registrar and proposer use separate narrowly permissioned accounts already granted on
the M4 contract. They are not Safe owners. Never request Safe-owner or deployer keys.

```powershell
# Process one due registrar job
python -m app.registrar_process --once

# Activate a reviewed, signed job and process one step
python -m app.registrar_process --activate-job <job-id> --once

# Process reviewed result intents
python -m app.proposer_process --once
```

Confirmation requires a successful receipt at the configured depth and a matching
contract read. An uncertain submission is quarantined and must be reconciled by receipt,
nonce, and contract state before any retry.

## PandaScore import and independent review

PandaScore is informational, never settlement authority. Configure
`PANDASCORE_USE_APPROVED=true` and the server-only token. Validate before writing:

```powershell
python -m scripts.import_pandascore all --max-pages 1 --validate-only
python -m scripts.import_pandascore all --max-pages 1
```

The import is additive/idempotent and preserves append-only result observations. View
scheduled fixtures with:

```text
GET /api/fixtures?match_status=scheduled&limit=100
```

An imported fixture must have independent non-PandaScore evidence before registration.
Record the operator decision with `scripts.review_fixture`; approval alone does not write
to Ethereum. The frontend/API now expose the latest operator review separately from the
provider observation. A reviewed fixture still becomes ineligible within 30 minutes of
its scheduled start.

## Live acceptance flow

1. Import a future fixture and record an independently reviewed organizer source.
2. In the frontend, connect a disposable Sepolia user wallet and sign the registration
   challenge/request. The registrar service—not the user—submits registration.
3. Wait for two confirmations, rerun the registrar, and sync the indexer. Confirm the
   fixture response contains `onchain_registration`.
4. The user claims the ACON test-token faucet allocation, approves the fixed subsidy,
   and calls `createMarket`. The backend never creates a normal user's market.
5. Use another disposable wallet for trading evidence: claim ACON, approve the quoted
   maximum cost, then buy. A frontend buy has two wallet steps. Confirm the history,
   portfolio, receipt, and contract balances after indexing.
6. Import the exact PandaScore match by provider ID after a result exists, independently
   review that exact observation, assess it, and run the proposer.
7. Exercise challenge, real VRF selection, five-resolver committee, three matching votes,
   settlement, and payouts. Sepolia deadlines elapse normally; use Anvil time controls for
   long timeout/replacement scenarios.

Never paste disposable or service private keys into chat, logs, screenshots, or commits.
If a key is exposed, treat the address as compromised and replace it. Resolver votes need
only the selected disposable resolver accounts; do not distribute all resolver keys or
Safe-owner keys to an agent.

## Recorded live smoke

The following evidence exists on the current M4 deployment:

- Fixture 98, MOUZ vs BetBoom, independently reviewed and registered at block `12052271`.
- Registration transaction: `0x9d81735ee6ae664bcf4cbe0cf278c527d65d54d8645def40d172b06d8d5c4739`.
- Market 0 created at block `12052289`.
- Market transaction: `0x1e4ea52d64f2d9c87e03e58311e7ca3217603b5455aa9dffd125f04d9e952f32`.
- YES buy indexed at block `12052315`.
- Trade transaction: `0x2d512622352ddd5e52dff710d2f2d3a00bf5ab84583ed7889fa7b1f9ec0f6400`.

Market 0 is useful for projection/UI evidence but its real trading deadline is fixed. Use
a newly reviewed future fixture for a later write demo.

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm test
npm run typecheck
npm run build
```

Last verified results during the live M4 integration: backend 129 passed; frontend 157
passed; typecheck and production build passed. `forge` was not installed on that Windows
machine, so contract tests must be run in Foundry CI or a workstation with Foundry.

## Common failures

- **CORS reports `200 OK` as failed:** frontend host and allowed origin differ between
  `localhost` and `127.0.0.1`; current backend code accepts both local equivalents.
- **RPC HTTP 400 during backfill:** use `INDEXER_BLOCK_BATCH_SIZE=10`.
- **PandaScore approval appears ignored:** run through project settings from `backend/`;
  the importer reads `.env` via `get_settings()`.
- **No chart points:** history is legitimately empty until a buy/sell is indexed.
- **Mined but not indexed:** wait for the two-confirmation safe block and ensure exactly
  one continuous indexer is running.
- **`registration_eligible: false`:** commonly unreviewed evidence, a past/near start,
  an existing result, or stale identity—not an API connectivity failure.
- **Transaction signing rejects `to`:** contract targets must be EIP-55 checksum addresses.
