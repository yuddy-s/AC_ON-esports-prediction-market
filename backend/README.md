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

Two confirmations are the approved Sepolia demo default; deployments may override the value. Before touching indexer state, the worker verifies `eth_chainId` against `INDEXER_CHAIN_ID` and validates the supplied ABI against the approved `MarketCreated` and `TradeExecuted` event contracts. It fails closed for a wrong network or while the final deployed ABI is unavailable.

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
- `GET http://localhost:8000/api/trades/by-transaction/{transaction_hash}`
- `GET http://localhost:8000/api/sample-matches`
- `GET http://localhost:8000/api/sample-matches/{slug}`

The sample-match endpoints are deprecated and non-authoritative. New frontend work should use the indexed endpoints.

### Frontend indexing synchronization

After the wallet reports a successful mined `buy`, poll `GET /api/trades/by-transaction/{transaction_hash}` with the receipt's `0x`-prefixed, 32-byte transaction hash. The path accepts upper- or lowercase hex and returns the hash in lowercase. An invalid hash returns HTTP 422. The response is:

```json
{
  "transaction_hash": "0x...",
  "items": []
}
```

`items` contains all confirmed `TradeExecuted` projections for that transaction on the active indexed contract, ordered by block and log index. Each item has the same fields as `/api/markets/{market_id}/trades`, including `market_id`, `transaction_hash`, `log_index`, and `authoritative: false`. HTTP 200 with an empty list means no matching trade has been indexed; it can also mean the indexer is not configured, the transaction is still inside the confirmation window, the transaction did not emit a trade, or the frontend is using another contract deployment. Do not interpret an empty list alone as a failed or pending wallet transaction.

`GET /api/indexer/status` includes `configured`, `chain_id`, `contract_address`, `latest_observed_block`, `last_safe_block`, `lag_blocks`, and `updated_at`. `updated_at` is the checkpoint's last update in UTC ISO 8601 format, or `null` before a head has been observed. Each successful head observation refreshes it, even if a later indexing range fails. Compare the status chain and contract with the wallet transaction, check that `updated_at` is recent, and wait until `last_safe_block` reaches the receipt block. If the trade lookup is still empty after that, inspect the receipt and its logs. A healthy two-confirmation worker normally has nonzero `lag_blocks`; zero lag alone does not prove that the worker is current. Database failures return a server error from indexed read endpoints rather than an empty trade list.

## Frontend Integration

If the frontend wants to fetch this fallback data, set:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Frontend display work is intentionally outside this backend scaffold.
