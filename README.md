# AC_ON Esports Prediction Market

AC_ON is a testnet-only decentralized esports prediction market for binary esports match outcomes. Users connect a Coinbase Wallet and eventually trade YES/NO shares on match results.

Milestone 3 is focused on one guarded YES/NO buy end to end: quote → wallet buy → mined `TradeExecuted` → indexer → API → frontend shows indexed. ACON and the LMSR market contract are deployed on Ethereum Sepolia, and a ten-share YES buy passed the live contract smoke test; the [versioned deployment handoff](deployments/README.md) includes addresses, ABIs, and confirmed creation/trade transactions. The full frontend → contract → indexer → API flow runs locally on an Anvil chain (see [Run the full M3 flow locally](#run-the-full-m3-flow-locally-anvil)); hosted indexer/API integration on Sepolia is pending.

## What Works Now

- React + Vite + TypeScript + Tailwind frontend.
- Coinbase Smart Wallet connection through wagmi/viem.
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
- `PredictionMarket` with creator-subsidy collection, LMSR `quoteBuy`, guarded `buy(..., maxCost)`, position reads, and `TradeExecuted` events. See [contract setup, ABI, and smoke-test instructions](contracts/README.md).
- A confirmed Sepolia guarded buy with exact payment/position checks and live decoding of both creation and trade events by the backend RPC client and ABI decoder. See the [deployment and smoke-test evidence](contracts/deployments/sepolia-m3-2026-10-21/README.md).
- Vitest unit tests for the frontend trade logic.
- CI workflow that tests and builds the frontend, applies backend migrations/tests, and runs Foundry formatting/build/tests.

## Important Boundaries

- Sample match data is fake Milestone 2 display data only.
- PostgreSQL/Supabase is not authoritative for real market state.
- Contracts are authoritative for market state and positions. M3 implements creation and guarded buys; settlement and payouts are deferred.
- Ethereum Sepolia (chain ID `11155111`) is the selected Milestone 3 testnet; the team is not planning a network migration during MVP integration.
- The full M3 quote-to-buy-to-indexer-to-frontend flow works on a local Anvil chain; the contracts are live on Sepolia but the hosted indexer/API is not yet. The old M2 address is not an M3 deployment.
- ACON is the test-only payment/collateral token; Sepolia ETH pays gas. Sells and payouts are not part of this implementation.
- The approved Milestone 3 decisions are recorded in [`docs/agent/interfaces/M3_TRADING_INTERFACE.md`](docs/agent/interfaces/M3_TRADING_INTERFACE.md). The [contracts README](contracts/README.md) documents the implemented ABI and remaining handoff review.

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
| `VITE_PREDICTION_MARKET_ADDRESS` | `PredictionMarket` address from the deployment handoff |
| `VITE_ACON_TOKEN_ADDRESS` | ACON token address from the deployment handoff |
| `VITE_DEMO_MARKET_ID` | Market shown on the page (default `0`) |
| `VITE_API_URL` | FastAPI backend, e.g. `http://localhost:8000`; used for the "indexed" step |
| `VITE_ANVIL_ACCOUNT` | Optional: which default Anvil account the local test wallet uses (default account #0) |

Restart `npm run dev` after changing env values. `.env.example` already has the Sepolia M3 addresses and lists the local Anvil ones. To keep a local Anvil `.env.local` and still try Sepolia, put the Sepolia values in `frontend/.env.sepolia.local` and run `npm run dev:sepolia`.

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

This runs the real contracts, indexer, API, and frontend on a local chain, without Sepolia ETH or a hosted database. Requires [Foundry](https://book.getfoundry.sh/getting-started/installation) and the backend virtual environment from above. On Windows, run these in Git Bash. Use four terminals from the repository root.

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

4. In `frontend/.env.local` set `VITE_CHAIN=anvil`, the two addresses above, and `VITE_API_URL=http://localhost:8000`. Then `npm run dev`, click **Connect Anvil test wallet (local only)**, and buy YES or NO. Account #0 already has ACON from the deployment; another account (set `VITE_ANVIL_ACCOUNT`) can claim the faucet first.

Restarting Anvil wipes the chain. Repeat step 2 (the addresses stay the same) and delete `backend/anvil-demo.db` before restarting the worker.

## Run Checks

Frontend:

```bash
cd frontend
npm test
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
```

## Not Here Yet

- Sell, settlement, claim, and complete VOID contract paths.
- A live guarded-buy demonstration on Ethereum Sepolia with Coinbase Smart Wallet through the hosted indexer/API (works locally on Anvil).
- Vercel deployment of the frontend.
- Oracle service implementation.
- Hosted indexer/database/API validation against the confirmed Sepolia creation and trade events.
- Resolver committee implementation.

## Notes

- The proposed Milestone 4 resolver design uses direct on-chain votes authorized by `msg.sender`, including Coinbase Smart Wallet transactions. It remains subject to explicit team approval. If relayed signed votes are added later, contract-wallet signatures must use EIP-1271 rather than relying only on `ecrecover`.
