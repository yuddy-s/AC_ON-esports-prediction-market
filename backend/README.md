# AC_ON Backend

FastAPI backend scaffold for Milestone 2. It serves fake sample match data from PostgreSQL/Supabase for display and fallback demos only.

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
- `GET http://localhost:8000/api/sample-matches`
- `GET http://localhost:8000/api/sample-matches/{slug}`

## Frontend Integration

If the frontend wants to fetch this fallback data, set:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Frontend display work is intentionally outside this backend scaffold.
