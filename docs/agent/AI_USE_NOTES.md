# M5 AI-Assistance Notes

These notes support transparent presentation reporting. They contain no credentials or raw
signatures.

## 2026-11-19 — Backend public integration and recovery

- The coding agent helped translate the team-approved cost constraint into an accurately documented
  hybrid topology: public Vercel frontend, free Render API, Supabase/Sepolia, and separate local
  operator-run workers.
- The human operator rotated the exposed database credential and authorized a one-time indexer
  catch-up plus safe recovery checks.
- The agent ran repository commands to verify Alembic revision `20261102_0008`, capture sanitized
  pre/post counts, advance the confirmed Sepolia checkpoint, and execute the public smoke test.
- The agent detected a real proposer restart failure against the Supabase transaction pooler,
  identified psycopg automatic prepared statements as the cause, implemented the narrow connection
  fix, added regression tests, and reran the original recovery scenario.
- Results were independently observable through the public API and shared database. The human team
  remains responsible for reviewing the PR, operating wallets, funding VRF, approving evidence,
  recording the presentation, and accepting residual risks.
