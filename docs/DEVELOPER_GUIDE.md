# AC_ON Developer Guide

Status: Milestone 5 draft. Public service URLs and deployment evidence are pending.

## System Model

The Sepolia contracts are authoritative for fixtures, markets, positions, resolver selection,
settlement, and payouts. FastAPI/PostgreSQL provide source workflows and derived reads. The indexer
waits for confirmations and can rebuild only chain-derived projections. Registrar and proposer are
separate least-privilege processes; PandaScore is informational and independently reviewed.

Authoritative public deployment data lives in `deployments/sepolia-2026-11-02`. Do not pair a
contract address with a different ABI or deployment block.

## Local Setup

1. Create `backend/.env` and `frontend/.env.local` from their examples. Both must remain ignored.
2. Create the backend virtual environment, install requirements, and run `alembic current` followed
   by `alembic upgrade head` only after reviewing the target database.
3. Install frontend dependencies with `npm ci`.
4. Start FastAPI, exactly one indexer, and the frontend using the M4 application runbook.
5. Start registrar/proposer only with separate configured accounts and the intended database/chain.

Never print secrets during diagnostics. Safe-owner and resolver keys do not belong in backend or
frontend configuration. Browser variables may contain only public chain, address, and API values.

## Verification Commands

```text
backend:  pytest
frontend: npm test; npm run typecheck; npm run build
contracts: forge fmt --check; forge build; forge test
```

GitHub Actions additionally runs ABI/source/runtime checks, pricing vectors, disposable Anvil
journeys, Slither, coverage, and secret scanning. M5 adds PostgreSQL integration and read-only
Playwright/public-smoke evidence in their owner PRs.

## Public Deployment

- Vercel serves the static frontend with public Sepolia contract/token and Render API values.
- Render runs one FastAPI service and exactly one each of indexer, registrar, and proposer.
- Supabase holds source/audit state and derived projections. Apply migrations once before workers.
- Configure the exact Vercel CORS origin. Health and indexer status are public, non-authoritative reads.
- PandaScore imports are operator-controlled; an imported result cannot reach the proposer without
  independent review.

Follow the M5 deployment plan for ordering, readiness, rollback, and evidence capture.

## Recovery

- Check Etherscan and contract state before retrying any uncertain signer transaction.
- On indexer staleness, stop duplicates, retain one worker, verify chain/address/ABI, then resume.
- Rebuild only chain-derived fixtures/markets/events/positions. Preserve provider observations,
  reviews, signed requests, assessments, intents, attempts, and audit history.
- During provider failure, retain the last observation and stop new proposal work rather than guess.
- For signer compromise, stop the worker, revoke the narrow role through the Safe, rotate/fund the
  replacement, reconcile pending nonces/receipts, and update only managed secrets.
- Never use destructive database reset/drop operations as routine recovery.

## Monitoring And Troubleshooting

- `/health`: API/database availability.
- `/api/v2/indexer/status`: configured chain/address/ABI, safe block, lag, and update timestamp.
- Expected Sepolia lag is normally two blocks. A previously current checkpoint may still look close
  while a worker is stopped, so check `updated_at` as well.
- Use the verified 10-block RPC log batch when the provider rejects larger requests.
- A browser CORS failure can report HTTP 200; verify the deployed Vercel origin exactly.
- A mined transaction is authoritative even if the indexer or UI is delayed. Do not duplicate writes.

## Documentation And Evidence Rules

Every implementation PR updates affected tests, API/deployment/recovery instructions, integration
results, and defect records. Evidence distinguishes CI, local Anvil, public Sepolia, and manual
browser execution. Store only sanitized public data in Git or CI artifacts.
