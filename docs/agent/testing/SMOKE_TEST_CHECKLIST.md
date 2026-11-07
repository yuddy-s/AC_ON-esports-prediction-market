# Release smoke-test checklist

One page to run before a demo, grading session or hosted release. Check every row against the
same deployment; a single mismatch (wrong chain, old address, old ABI) explains most "it shows
nothing" failures. Owners: Adriel (frontend/wallet rows) and Yudhveer (backend/indexer rows).
Record the date, who ran it and the result of each row.

Current M4 Sepolia values come from
[`deployments/sepolia-2026-11-02/manifest.post-setup.json`](../../../deployments/sepolia-2026-11-02/manifest.post-setup.json).
For local Anvil, use chain `31337` and the addresses printed by your local deployment.

## 1. Deployment identity

| # | Check | Expected (M4 Sepolia) | How |
|---|---|---|---|
| 1.1 | Chain ID | `11155111` | Frontend `VITE_CHAIN=sepolia`; backend `INDEXER_CHAIN_ID`; `GET /api/v2/indexer/status` → `chain_id` |
| 1.2 | PredictionMarket address | `0x03ae48f03C7822540a91DA2168602bd49dC510E9` | Same value in `frontend/.env.local`, backend `PREDICTION_MARKET_ADDRESS`, indexer status `contract_address`, and Etherscan |
| 1.3 | ACON token address | `0xf85b2278a810410c6AE0b7490d34671E0C8e6E90` | Frontend `VITE_ACON_TOKEN_ADDRESS`; manifest |
| 1.4 | ABI version | `PredictionMarket.721a6fef039a.4af9297937eb.abi.json` (source `721a6fef…`) | Backend `PREDICTION_MARKET_ABI_PATH`; the frontend bundles the M4 ABI. Never pair this address with the M3 ABI |
| 1.5 | Deployment block | market block `12051223` | Backend `PREDICTION_MARKET_DEPLOYMENT_BLOCK`; manifest |

## 2. Backend and indexer

| # | Check | Expected | How |
|---|---|---|---|
| 2.1 | Database migration | `20261102_0008` (M4 projections) or later | `alembic current` in `backend/` against the intended database |
| 2.2 | API health | `200 OK` | `GET /health` |
| 2.3 | Indexer configured for the same deployment | `configured: true`, matching chain and address | `GET /api/v2/indexer/status` |
| 2.4 | Indexer checkpoint is moving | `last_safe_block` advances; `updated_at` under 2 minutes old | Call 2.3 twice a minute apart. Two-confirmation lag is normal |
| 2.5 | One worker per database | Exactly one indexer worker running | Process list / Render dashboard |
| 2.6 | Indexed reads | Markets list includes the expected market; trades match Etherscan | `GET /api/v2/markets`, then compare one trade hash with Etherscan |

## 3. Frontend and wallet states

| # | Check | Expected |
|---|---|---|
| 3.1 | Page loads with no wallet | Markets, fixtures, prices and history load read-only |
| 3.2 | Wrong network | Clear "switch network" prompt; no write buttons enabled |
| 3.3 | Connected, no ACON | Faucet offered; buy disabled with a reason |
| 3.4 | Buy | Wallet → submitted → mined → indexed; position updates from the contract |
| 3.5 | Sell | Same states; minimum return shown; position decreases |
| 3.6 | Rejected in wallet | "Rejected" message; no state change |
| 3.7 | Reverted (stale quote / guard) | "Reverted" message; balances unchanged |
| 3.8 | Indexer stale or unreachable | Trade stays at "mined" with a stale-indexer notice; contract reads still work |
| 3.9 | Resolution views | Proposal, challenge, selection/vote and final status match the contract state |
| 3.10 | Claim | Claim succeeds once; second claim is blocked |

## 4. Sign-off

| Date | Run by | Chain | Result | Notes / failing rows |
|---|---|---|---|---|
| | | | | |
