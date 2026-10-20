# AC_ON Backend

FastAPI backend and Milestone 3 indexer foundation. The indexed market/trade APIs expose derived Ethereum Sepolia projections. The older sample-match endpoints remain temporarily as deprecated Milestone 2 fallback data.

This data is **non-authoritative**. Blockchain contracts remain the source of truth for real markets, balances, settlement, and payouts.

## Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set `DATABASE_URL` to the Supabase PostgreSQL connection string.

Apply schema migrations before running the API or indexer:

```bash
alembic upgrade head
```

Indexer configuration is environment-driven:

```env
INDEXER_CHAIN_ID=11155111
SEPOLIA_RPC_URL=https://your-sepolia-rpc.example
PREDICTION_MARKET_ADDRESS=0x...
PREDICTION_MARKET_DEPLOYMENT_BLOCK=0
INDEXER_CONFIRMATION_DEPTH=2
INDEXER_POLL_INTERVAL_SECONDS=5
INDEXER_BLOCK_BATCH_SIZE=500
INDEXER_RPC_TIMEOUT_SECONDS=10
INDEXER_RPC_MAX_ATTEMPTS=3
INDEXER_RPC_BACKOFF_SECONDS=0.5
PREDICTION_MARKET_ABI_PATH=path/to/PredictionMarket.json
```

Two confirmations are the approved Sepolia demo default; deployments may override the value. The worker validates the supplied ABI against the approved `MarketCreated` and `TradeExecuted` event contracts before reading or advancing a checkpoint. It fails closed while the final deployed ABI is unavailable.

Run one backfill/live synchronization pass, continuous polling, or a deterministic rebuild:

```bash
python -m app.indexer.worker --once
python -m app.indexer.worker
python -m app.indexer.worker --rebuild
```

The JSON-RPC transport retries bounded transient failures and splits provider-rejected block ranges. Run only one worker instance for the Milestone 3 deployment.

## Seed Sample Data

```bash
python -m scripts.seed_sample_matches
```

The seed script creates the `sample_matches` table if needed and upserts three fake sample matches.

## Run Locally

```bash
uvicorn app.main:app --reload
```

Useful endpoints:

- `GET http://localhost:8000/health`
- `GET http://localhost:8000/api/indexer/status`
- `GET http://localhost:8000/api/markets`
- `GET http://localhost:8000/api/markets/{market_id}`
- `GET http://localhost:8000/api/markets/{market_id}/trades`
- `GET http://localhost:8000/api/sample-matches`
- `GET http://localhost:8000/api/sample-matches/{slug}`

The sample-match endpoints are deprecated and non-authoritative. New frontend work should use the indexed endpoints.

## Frontend Integration

If the frontend wants to fetch this fallback data, set:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Frontend display work is intentionally outside this backend scaffold.
