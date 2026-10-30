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

Indexer configuration is environment-driven. For the deployed M3 market, with the worker launched from `backend/`, use these public values and set the RPC URL privately:

```env
INDEXER_CHAIN_ID=11155111
SEPOLIA_RPC_URL=https://your-sepolia-rpc.example
PREDICTION_MARKET_ADDRESS=0x19EF739001038Ce9DFB1E12Cf45A10c9250A60a7
PREDICTION_MARKET_DEPLOYMENT_BLOCK=11963761
INDEXER_CONFIRMATION_DEPTH=2
INDEXER_POLL_INTERVAL_SECONDS=5
INDEXER_BLOCK_BATCH_SIZE=500
INDEXER_RPC_TIMEOUT_SECONDS=10
INDEXER_RPC_MAX_ATTEMPTS=3
INDEXER_RPC_BACKOFF_SECONDS=0.5
PREDICTION_MARKET_ABI_PATH=../deployments/abi/PredictionMarket.6e30d516669e.792fa9f230ed.abi.json
```

Two confirmations are the approved Sepolia demo default; deployments may override the value. Before touching indexer state, the worker verifies `eth_chainId` against `INDEXER_CHAIN_ID` and validates the supplied ABI against the approved `MarketCreated` and `TradeExecuted` event contracts. It fails closed for a wrong network or while the final deployed ABI is unavailable.

The completed [M3 manifest](../deployments/sepolia-m3.json) follows the [public deployment handoff convention](../deployments/README.md) and passes `python -m scripts.validate_handoff ../deployments/sepolia-m3.json`. It records the deployed source, token/market addresses, exact-build ABIs, and successful creation/buy receipts. The worker records the ABI filename as its version and refuses to resume an existing contract record with a different ABI version or deployment block. Use the completed manifest, not `sepolia-m3.template.json`.

Run one backfill/live synchronization pass, continuous polling, or a deterministic rebuild:

```bash
python -m app.indexer.worker --once
python -m app.indexer.worker
python -m app.indexer.worker --rebuild
```

The JSON-RPC transport retries bounded transient failures and splits provider-rejected block ranges. Run only one worker instance for the Milestone 3 deployment.

The real backend RPC client and ABI decoder have fetched and decoded the confirmed creation and guarded-buy events. On 2026-10-22, a local worker populated the configured Supabase database and the read-only smoke check passed against a local FastAPI instance. Persistent hosted worker/API operation and deployed-frontend acceptance remain pending. Once the worker has indexed the manifest's trade and the API is running against the same database, run the read-only cross-layer check:

```bash
python -m scripts.smoke_sepolia --manifest ../deployments/sepolia-m3.json --api-base-url https://YOUR_API_HOST
```

Set `SEPOLIA_RPC_URL` privately in the environment for this command. The smoke test reads `PredictionMarket.paymentToken()` and requires it to match the handoff's ACON token address. It also checks the canonical `MarketCreated`/`TradeExecuted` logs, status freshness and safe checkpoint, market projection, and transaction-hash trade lookup. It submits no transactions.

The known trade is `0xe5f5ff239ff3939cfc34c1c7719f2b1db9ef83d75f77f501236d004cb2d10c16` in block `11964663`, log index `104`: ten YES shares for `5249584441082326050` ACON base units. Its [receipt and event fixture](../contracts/deployments/sepolia-m3-2026-10-21/guarded-buy.json) includes exact payment/position checks. Market `0` stops accepting new buys at **2026-10-28 17:01:12 UTC**; the recorded events remain usable for read-only indexing validation afterward.

## Seed Sample Data

```bash
python -m scripts.seed_sample_matches
```

The seed script creates the `sample_matches` table if needed and upserts three fake sample matches.

## Milestone 4 Fixture Catalog (first backend slice)

The fixture catalog is imported **off-chain source data**, not an on-chain registration or market. An operator imports a JSON file from `backend/` after `alembic upgrade head` has applied revision `20261029_0002` to the chosen database. Use a local database for development; do not point the importer at Supabase unintentionally. No PandaScore account, API token, registrar key, or M4 ABI is needed for this slice.

```bash
python -m scripts.import_fixtures path/to/fixtures.json --validate-only
python -m scripts.import_fixtures path/to/fixtures.json
```

The file has `fixtures` and `results` arrays. A later file may contain only `results` for fixtures already imported. IDs are source identifiers, not the on-chain fixture key; Benny's exact `abi.encode` types remain to be frozen. Example **fictional** record:

```json
{
  "fixtures": [{
    "provider_id": "acon-mock", "game_id": "valorant", "external_match_id": "demo-1",
    "scheduled_start": "2030-01-01T18:00:00Z", "match_status": "scheduled",
    "team_a_id": "alpha", "team_a_name": "Mock Alpha",
    "team_b_id": "bravo", "team_b_name": "Mock Bravo",
    "evidence_url": "https://example.org/fictional-demo-schedule",
    "evidence_hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "source_updated_at": "2029-12-01T12:00:00Z"
  }],
  "results": [{
    "provider_id": "acon-mock", "game_id": "valorant", "external_match_id": "demo-1",
    "match_status": "completed", "winner_team_id": "alpha",
    "source_updated_at": "2030-01-01T21:00:00Z",
    "evidence_url": "https://example.org/fictional-demo-result",
    "evidence_hash": "0x1111111111111111111111111111111111111111111111111111111111111111"
  }]
}
```

Results are append-only observations with their evidence reference and hash; importing the same file twice does not duplicate rows. A different result remains visible in `/api/fixtures/{id}/results` rather than silently replacing the earlier one. The importer checks the winner against the fixture's two team IDs; it does not independently verify an organizer or settle a market. The JSON source is operated by the team and is never accepted through a public write endpoint.

- `GET /api/fixtures?game_id=valorant&match_status=scheduled&limit=50&offset=0` returns paginated fixture records.
- `GET /api/fixtures/{id}` returns one fixture and its latest result observation, or 404.
- `GET /api/fixtures/{id}/results` returns all source observations oldest first.

All catalog responses are non-authoritative. Registration status, linked market, on-demand wallet requests, and result-proposer automation are later M4 PRs; the M3 market/trade indexer continues to use its existing deployment and ABI.

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

To fetch the indexed API from the frontend, set this in `frontend/.env.local` (see [Frontend configuration](../README.md#frontend-configuration)):

```text
VITE_API_URL=http://localhost:8000
```

Also set the backend's `FRONTEND_ORIGIN` to the frontend's origin (for example `http://localhost:5173`) so CORS allows the requests.

The frontend should use the indexed endpoints above for M3 market and trade state. The sample-match endpoints remain deprecated M2 fallback data.
