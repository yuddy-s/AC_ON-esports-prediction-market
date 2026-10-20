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
```

Two confirmations are the approved Sepolia demo default; deployments may override the value. The provider/decoder runner will be connected after the approved Milestone 3 trade ABI is implemented. The current service and tests consume normalized chain logs through a provider interface.

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
