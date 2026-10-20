# AC_ON Esports Prediction Market

AC_ON is a testnet-only decentralized esports prediction market for binary esports match outcomes. Users connect a Coinbase Wallet and eventually trade YES/NO shares on match results.

Milestone 2 is focused on proving the architecture can run end to end. The current repo has a working frontend wallet prototype, a FastAPI backend scaffold, Supabase/PostgreSQL-backed fake sample match data, and GitHub Actions CI.

## What Works Now

- React + Vite + TypeScript + Tailwind frontend.
- Coinbase Smart Wallet connection through wagmi/viem.
- Connected wallet address and testnet balance display.
- Frontend reads a placeholder market (`getMarket(0)`) from the deployed `PredictionMarket` contract. Set the address in `frontend/src/predictionMarket.ts`.
- FastAPI backend with health and sample-match endpoints.
- Supabase PostgreSQL connection through `DATABASE_URL`.
- Repeatable seed script for three fake sample matches.
- CI workflow that builds the frontend and runs backend tests.

## Important Boundaries

- Sample match data is fake Milestone 2 display data only.
- PostgreSQL/Supabase is not authoritative for real market state.
- Ethereum Sepolia smart contracts are the source of truth for markets, trades, settlement, and payouts.
- Ethereum Sepolia (chain ID `11155111`) is the selected Milestone 3 testnet; the team is not planning a network migration during MVP integration.
- The frontend, contract, and backend are not connected to each other yet (Milestone 3).
- The approved Milestone 3 payment token, LMSR boundary, guarded-buy ABI, events, and deployment handoff are recorded in [`docs/agent/interfaces/M3_TRADING_INTERFACE.md`](docs/agent/interfaces/M3_TRADING_INTERFACE.md); they are not yet implemented by the current prototype.

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

Click **Connect Wallet** and sign in with a passkey (Coinbase Smart Wallet, no extension needed).

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
http://localhost:8000/api/sample-matches
http://localhost:8000/api/sample-matches/valorant-sentinels-loud
```

`/docs` lists every endpoint. Click an endpoint, then **Try it out**, then **Execute**.

## Run Checks

Frontend:

```bash
cd frontend
npm run build
```

Backend (with the virtual environment activated):

```bash
cd backend
python -m pytest
```

## Not Here Yet

- Full Solidity contracts (only a placeholder market exists).
- A fresh Ethereum Sepolia deployment of the eventual Milestone 3 contract.
- Contract writes and a trading UI in the frontend.
- Real on-chain markets/trading.
- Oracle service implementation.
- Indexer implementation.
- Resolver committee implementation.

## Notes

- Coinbase Smart Wallet is a contract wallet (ERC-4337), so any signature checks in the resolver contract need EIP-1271 support, not just `ecrecover`.
