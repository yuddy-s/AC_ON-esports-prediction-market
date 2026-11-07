# AC_ON Esports Prediction Market

AC_ON is a testnet-only decentralized esports prediction market for binary esports match outcomes. Users connect an Ethereum wallet and trade YES/NO shares on match results.

Milestone 4 is feature-complete and was promoted to `main` in PR #49. The application includes
normalized fixtures, guarded buys/sells, proposals/challenges, VRF resolver rounds,
settlement/VOID, claims, creator surplus, M4 indexed APIs, signer gateways, portfolio/resolution UI,
and operator-gated PandaScore ingestion. The [exact ABI and handoff](deployments/README.md) pair the
current implementation with the fresh M4 Sepolia deployment.

Milestone 5 now owns public Vercel/Render/Supabase integration, expanded integration and recovery
testing, remaining Sepolia lifecycle evidence, defect reporting, and draft user/developer guides.
The historical M3 handoff remains available only as an earlier release record.

## What Works Now

- React + Vite + TypeScript + Tailwind frontend.
- Coinbase Smart Wallet, MetaMask/injected-wallet, and local Anvil development-wallet connections through wagmi/viem.
- Connected wallet address and testnet balance display.
- Frontend market card with YES/NO LMSR prices and a trading-open/closed check (OPEN state and deadline).
- ACON balance and one-time faucet claim in the frontend.
- Frontend trade form: live `quoteBuy`, slippage-guarded `buy(..., maxCost)`, ACON approval when needed, and separate wallet / submitted / mined / indexed transaction states with user-facing error messages.
- Indexer-derived trade rows and the indexed transaction state appear only when the API reports the same chain and PredictionMarket address as the frontend. The UI reports a checkpoint older than two minutes while preserving the mined on-chain state.
- Contract addresses and API URL come from `VITE_*` env vars (see [Frontend configuration](#frontend-configuration)).
- FastAPI backend with health and sample-match endpoints.
- Supabase PostgreSQL connection through `DATABASE_URL`.
- Repeatable seed script for three fake sample matches.
- `ACONTestToken` with 18 decimals and a one-time 1,000 ACON faucet per address.
- Current `PredictionMarket` with fixture registration, subsidy-funded creation, guarded buys/sells, immutable proposals, bonded challenges, VRF selection/votes/timeouts, winning/VOID claims and creator surplus. See [contract setup, ABI, and smoke-test instructions](contracts/README.md).
- A confirmed Sepolia guarded buy with exact payment/position checks and live decoding of both creation and trade events by the backend RPC client and ABI decoder. See the [deployment and smoke-test evidence](contracts/deployments/sepolia-m3-2026-10-21/README.md).
- Vitest unit tests for the frontend trade logic.
- CI workflow that tests and builds the frontend, applies backend migrations/tests, and runs Foundry formatting/build/tests, exact ABI checks, local Anvil journeys, static analysis and coverage.

## Important Boundaries

- Sample match data is fake Milestone 2 display data only.
- PostgreSQL/Supabase is not authoritative for real market state.
- Contracts are authoritative for market state, positions, resolution and payouts. The M4
  implementation and Sepolia deployment are merged; public hosted integration is active M5 work.
- Ethereum Sepolia (chain ID `11155111`) is the selected Milestone 3 testnet; the team is not planning a network migration during MVP integration.
- The full M3 quote-to-buy-to-indexer-to-frontend flow works on a local Anvil chain; the contracts are live on Sepolia but the hosted indexer/API is not yet. The old M2 address is not an M3 deployment.
- ACON is the test-only payment/collateral token; Sepolia ETH pays gas. The current M4 deployment
  and consumers support buys, sells, resolution, and payouts; the M3 deployment is historical.
- The [current contract ABI](docs/agent/interfaces/CONTRACT_ABI.md) describes the implementation; the [M3 interface](docs/agent/interfaces/M3_TRADING_INTERFACE.md) describes the historical deployment. Pair addresses and ABIs from the same release.
- The [Milestone 5 plan](docs/agent/milestones/MILESTONE_5.md) defines current testing,
  public-deployment, evidence, defect, and draft-guide work. The M4 design remains frozen.

## Quick Start (macOS / Linux)

Requires Git, Node.js LTS, and Python 3. Use two terminal windows.

Terminal 1, frontend:

```bash
git clone https://github.com/yuddy-s/AC_ON-esports-prediction-market.git
cd AC_ON-esports-prediction-market
git checkout dev
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

Terminal 2, backend (open a new terminal in the same folder where you ran `git clone`):

```bash
cd AC_ON-esports-prediction-market/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="sqlite:///demo.db"
alembic upgrade head
python -m scripts.seed_sample_matches
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs (or `/api/sample-matches` and `/health`). Windows commands and the Supabase option are in the sections below.

## Get The Code

Requires [Git](https://git-scm.com/). `main` and `dev` are protected: create a branch from `dev` and open a pull request into `dev`.

```bash
git clone https://github.com/yuddy-s/AC_ON-esports-prediction-market.git
cd AC_ON-esports-prediction-market
git checkout dev
```

## Run The Frontend

Requires Node.js LTS. Works the same on macOS, Linux, and Windows.

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Before the first run, create `frontend/.env.local` (see [Frontend configuration](#frontend-configuration)). Without contract addresses the page loads but cannot read a market.

Click **Connect Wallet** and sign in with a passkey (Coinbase Smart Wallet, no extension needed). Coinbase Smart Wallet can connect and read on Ethereum Sepolia but cannot send transactions there (it fails with "Sepolia is not supported"), so to claim ACON or trade on Sepolia use **Connect MetaMask (browser wallet)** with MetaMask set to the Sepolia network. On a local Anvil chain use **Connect Anvil test wallet (local only)**.

### Frontend configuration

Copy `frontend/.env.example` to `frontend/.env.local` (gitignored) and fill it in. Only `VITE_*` values reach the browser, so never put private keys, RPC secrets, or database URLs here.

| Variable | Meaning |
|---|---|
| `VITE_CHAIN` | `sepolia` (default) for the real demo, `anvil` for a local chain on `127.0.0.1:8545` |
| `VITE_PREDICTION_MARKET_ADDRESS` | `PredictionMarket` address from the deployment handoff. The frontend uses the **M4** ABI (`deployments/abi`), so pair it with the [M4 Sepolia deployment](deployments/sepolia-2026-11-02/README.md) or a local M4 Anvil deployment; the M3 Sepolia deployment is not compatible |
| `VITE_ACON_TOKEN_ADDRESS` | ACON token address from the deployment handoff |
| `VITE_DEMO_MARKET_ID` | Featured market, listed first on the markets page (default `0`) |
| `VITE_API_URL` | FastAPI backend, e.g. `http://localhost:8000`; used for the "indexed" step |
| `VITE_ANVIL_ACCOUNT` | Optional: which default Anvil account the local test wallet uses (default account #0) |
| `VITE_FIXTURE_SOURCE` | Optional: `api` reads the fixture catalog from the backend's `/api/fixtures` (default when `VITE_API_URL` is set); `mock` shows fictional fixtures bundled with the frontend |

Restart `npm run dev` after changing env values. `.env.example` already has the M4 Sepolia addresses (market `0x03ae48f03C7822540a91DA2168602bd49dC510E9`, ACON `0xf85b2278a810410c6AE0b7490d34671E0C8e6E90`) and explains the local Anvil ones. The API at `VITE_API_URL` must index the same chain and market address; otherwise the price chart, trade history and "indexed" step stay hidden while contract reads still work. To keep a local Anvil `.env.local` and still try Sepolia, put the Sepolia values in `frontend/.env.sepolia.local` and run `npm run dev:sepolia`.

## Run The Backend

Requires Python 3.12 or newer (3.13 also works). Open a second terminal so the frontend keeps running.

### 1. Create a virtual environment and install dependencies

macOS / Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Choose a database

**Option A: local SQLite (quickest, no password needed).** Good for demos and testing. Set `DATABASE_URL` in the same terminal you will run the backend from (it resets when you open a new terminal):

macOS / Linux:

```bash
export DATABASE_URL="sqlite:///demo.db"
```

Windows (PowerShell):

```powershell
$env:DATABASE_URL = "sqlite:///demo.db"
```

**Option B: Supabase PostgreSQL (shared team database).** Copy `.env.example` to `.env` (`cp .env.example .env` on macOS/Linux, `copy .env.example .env` on Windows), then edit `backend/.env` and set `DATABASE_URL` to the Supabase connection string. Ask Yudhveer for it; never commit it. Use the SQLAlchemy psycopg format:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require
FRONTEND_ORIGIN=http://localhost:5173
```

### 3. Seed and run

Seed the fake sample matches:

```bash
alembic upgrade head
python -m scripts.seed_sample_matches
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

Keep this terminal open while you use the backend. If port 8000 is already in use, add `--port 8010` and use `8010` in the URLs below.

Open these in your browser (the bare address `http://localhost:8000/` shows "Not Found" because no page is defined there):

```text
http://localhost:8000/docs
http://localhost:8000/health
http://localhost:8000/api/indexer/status
http://localhost:8000/api/markets
http://localhost:8000/api/sample-matches
http://localhost:8000/api/sample-matches/valorant-sentinels-loud
```

`/docs` lists every endpoint. Click an endpoint, then **Try it out**, then **Execute**.

## Run The Full M3 Flow Locally (Anvil)

This runs the real contracts, indexer, API, and frontend on a local chain, without Sepolia ETH or a hosted database. Requires [Foundry](https://book.getfoundry.sh/getting-started/installation) and the backend virtual environment from above. On Windows, run these in Git Bash. Use four terminals from the repository root; reuse the deployment terminal for the frontend after step 2.

1. Start a local chain (2-second blocks). Leave it running:

   ```bash
   anvil --block-time 2
   ```

2. Deploy ACON, `PredictionMarket`, and demo market `#0`. Anvil prints ten test accounts at startup; use the private key of account `(0)`. It is a public Anvil test key, not a real wallet:

   ```bash
   git submodule update --init --recursive
   cd contracts
   export SEPOLIA_PRIVATE_KEY=<anvil account (0) private key>
   forge script script/Deploy.s.sol:DeployPredictionMarket --rpc-url http://127.0.0.1:8545 --broadcast
   ```

   On a fresh Anvil the token deploys to `0x5FbDB2315678afecb367f032d93F642f64180aa3` and the market to `0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512`.

3. Run the backend API and the indexer worker against Anvil (two terminals, both with the virtual environment activated and these variables set):

   ```bash
   cd backend
   export DATABASE_URL="sqlite:///anvil-demo.db"
   export INDEXER_CHAIN_ID=31337
   export SEPOLIA_RPC_URL="http://127.0.0.1:8545"
   export PREDICTION_MARKET_ADDRESS="0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"
   export PREDICTION_MARKET_DEPLOYMENT_BLOCK=0
   export PREDICTION_MARKET_ABI_PATH="../contracts/out/PredictionMarket.sol/PredictionMarket.json"
   alembic upgrade head
   uvicorn app.main:app --port 8000      # terminal 3
   python -m app.indexer.worker          # terminal 4
   ```

   SQLite is fine for local testing, but it stores the 78-digit amounts approximately (the last digits of an indexed cost can differ from the chain). Use PostgreSQL/Supabase for exact values.

4. In `frontend/.env.local` set `VITE_CHAIN=anvil`, the two addresses above, and `VITE_API_URL=http://localhost:8000`. In the deployment terminal, run `cd ../frontend` and `npm run dev`, click **Connect Anvil test wallet (local only)**, and buy YES or NO. Account #0 already has ACON from the deployment; another account (set `VITE_ANVIL_ACCOUNT`) can claim the faucet first.

Restarting Anvil wipes the chain. Repeat step 2 (the addresses stay the same) and delete `backend/anvil-demo.db` before restarting the worker.

## Run The Sepolia App Locally

This uses the deployed M3 contracts and a locally running API/indexer. Use PostgreSQL (local or Supabase) for exact indexed token amounts. You need a Sepolia RPC URL; keep its API key and the database URL only in the ignored `backend/.env`. If another worker already uses that database, stop it or use a separate database: run exactly one worker per indexed deployment.

1. Create the backend virtual environment as described above. Copy `backend/.env.example` to `backend/.env` if it does not exist, then set `DATABASE_URL`, `FRONTEND_ORIGIN=http://localhost:5173`, your private `SEPOLIA_RPC_URL`, and these public values:

   ```env
   INDEXER_CHAIN_ID=11155111
   PREDICTION_MARKET_ADDRESS=0x19EF739001038Ce9DFB1E12Cf45A10c9250A60a7
   PREDICTION_MARKET_DEPLOYMENT_BLOCK=11963761
   PREDICTION_MARKET_ABI_PATH=../deployments/abi/PredictionMarket.6e30d516669e.792fa9f230ed.abi.json
   INDEXER_CONFIRMATION_DEPTH=2
   ```

2. From `backend/`, apply the migration and backfill the confirmed events. Keep the single worker polling in one terminal, and start the API in another terminal from `backend/` with the same `.env`:

   ```bash
   alembic upgrade head
   python -m app.indexer.worker --once
   python -m app.indexer.worker
   ```

   ```bash
   uvicorn app.main:app --host localhost --port 8000
   ```

3. Copy `frontend/.env.example` to ignored `frontend/.env.local`. Its Sepolia contract addresses and market ID are already filled in; set `VITE_API_URL=http://localhost:8000`. From `frontend/`, run `npm ci` and `npm run dev`. Open `http://localhost:5173`. Use MetaMask on Sepolia for faucet claims and buys; the wallet needs Sepolia ETH for gas. The seeded question is demo content, but market state and indexed trades come from real Sepolia transactions.

4. Check `http://localhost:8000/api/indexer/status` for the expected chain/address, a recent `updated_at`, and a safe checkpoint past the known buy block `11964663`. Check `/api/markets/0/trades` for the recorded trade. From `backend/`, run the read-only reconciliation check:

   ```bash
   python -m scripts.smoke_sepolia --manifest ../deployments/sepolia-m3.json --api-base-url http://localhost:8000
   ```

This verifies Sepolia events against the database and local API. The complete browser trading flow has been verified on local Anvil. A browser-initiated Sepolia buy and a Render/Vercel deployment remain separate follow-ups; describe them as pending if presenting this local setup.

## Run Checks

Frontend:

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

Backend (with the virtual environment activated):

```bash
cd backend
python -m pytest
```

Contracts (after initializing the pinned submodule as described in `contracts/README.md`):

```bash
cd contracts
forge fmt --check
forge build
forge build script/Deploy.s.sol
forge test
python3 script/export_handoff.py --check
python3 script/smoke.py --start-anvil
```

The frontend no longer advertises a lint command without an ESLint configuration. TypeScript checking runs locally and in CI. A configured lint rule set can be added later as a separate check.

## Dependency Security Follow-Up

On 2026-10-22, `npm audit --omit=dev` reported **25 production dependency findings**: 23 moderate, 2 high (`follow-redirects` and `ws`), and 0 critical.

On 2026-11-07 the frontend owner (Adriel) applied every non-breaking fix (`npm audit fix`, lockfile only) and reran tests (159 passing), typecheck and build. `npm audit --omit=dev` went from 29 findings (12 moderate, 17 high) to **27 (11 moderate, 16 high, 0 critical)**. Every remaining finding comes from four transitive packages pulled in by the wallet stack (`wagmi` 2 → WalletConnect/Reown, Coinbase SDK):

| Package | Severity | Issue | Exposure in this app |
|---|---|---|---|
| `ws` | high | Memory-exhaustion DoS; uninitialized memory disclosure | Wallet-connector WebSocket client in the browser; no server in this app accepts `ws` connections |
| `zod` | high | Memory exhaustion validating oversized collections | Used inside wallet libraries on wallet/RPC responses, not on user input we accept |
| `decode-uri-component` | high | DoS from malformed percent-encoding | WalletConnect URL parsing in the user's own browser tab |
| `uuid` | moderate | Missing buffer bounds check when `buf` is passed | Wallet libraries call it without a caller buffer |

The only automatic fix is `npm audit fix --force`, which upgrades `wagmi` 2 → 3 (a breaking major). **Mitigation:** the app is testnet-only and these packages run client-side in the user's own browser, not on a server we host. **Owner:** Adriel. **Plan (M5):** upgrade `wagmi`/`viem` together on a separate branch before public Vercel hosting, then rerun the wallet, trade, claim, build and audit checks. Do not apply the major upgrade without that integration testing.

## Not Here Yet

- Fresh M4 deployment, Safe/VRF and service-role setup, and frontend/backend integration of the merged lifecycle.
- A hosted Ethereum Sepolia guarded-buy demonstration through the deployed frontend, indexer, and API. Use MetaMask for Sepolia writes; Coinbase Smart Wallet currently supports reads there but not transactions.
- Vercel deployment of the frontend.
- Oracle service implementation.
- Persistent Render worker/API validation against the confirmed Sepolia creation and trade events.
- Real Safe/VRF subscription setup and focused Sepolia resolver/settlement smoke for the current contracts.

## Notes

- The PR #28-approved Milestone 4 resolver design uses direct on-chain votes authorized by `msg.sender`. On Sepolia, resolver writes use MetaMask or another supported injected wallet because Coinbase Smart Wallet currently cannot submit transactions there. Relayed voting is outside M4; if added later, contract-wallet signatures must use EIP-1271 rather than relying only on `ecrecover`.
