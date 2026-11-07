# M5 Public Deployment And Rollback Plan

Status: draft plan. Public URLs and execution evidence remain pending.

## Target Topology

```text
Browser / MetaMask
  -> Vercel static frontend
       -> Render FastAPI web service
            -> Supabase PostgreSQL
       -> Ethereum Sepolia RPC / M4 contracts

Render indexer worker (exactly one) -> Sepolia logs -> Supabase projections
Render registrar worker             -> approved jobs -> Sepolia registrar role
Render proposer worker              -> reviewed intents -> Sepolia proposer role
Operator-only PandaScore import/review -> Supabase source and audit rows
```

The Safe owns administration and the VRF subscription. Safe-owner and resolver keys are never
hosted. Render signers are separate least-privilege accounts. Contracts remain authoritative.

## Configuration Ownership

| Location | Public values | Secret values | Owner |
|---|---|---|---|
| Vercel | chain ID, contract/token addresses, Render API URL | none | Adriel |
| Render web/indexer | chain/address/deployment block, ABI path, confirmation depth | database URL, RPC URL | Yudhveer |
| Render registrar | public contract configuration | database, RPC, registrar key | Yudhveer |
| Render proposer | public contract configuration | database, RPC, proposer key | Yudhveer |
| Operator environment | provider selection | PandaScore token and review access | Yudhveer |
| Team custody | Safe/VRF/resolver public configuration | Safe-owner and resolver keys | Benny/team; never hosted |

Use the post-setup manifest and frozen ABI in `deployments/sepolia-2026-11-02`. Configure the
exact Vercel origin in backend CORS. Keep indexer confirmation depth at two and the verified RPC
batch size at ten unless a new provider is tested.

## Deployment Order

1. Rotate the exposed disposable challenger wallet; verify Git ignore and secret scanning.
2. Back up Supabase and record table counts plus current Alembic revision.
3. Apply `alembic upgrade head`; verify revision `20261102_0008` and preserved counts.
4. Deploy the Render web service and verify `/health` without exposing configuration.
5. Start exactly one indexer; verify chain/address/ABI, safe-block advancement, and two-block lag.
6. Start isolated registrar and proposer workers; verify roles/balances before accepting jobs.
7. Deploy Vercel with the public Render URL and exact Sepolia addresses.
8. Run public smoke and Playwright reads, then controlled MetaMask acceptance transactions.
9. Record sanitized results in the integration ledger before declaring the release healthy.

## Readiness And Monitoring

- Web readiness: `/health` reports API and database availability.
- Indexer readiness: `/api/v2/indexer/status` matches chain/address/ABI and advances recently.
- Alert conditions: unavailable health, stale `updated_at`, lag above the documented threshold,
  repeated RPC/provider errors, failed/quarantined signer jobs, or migration mismatch.
- Logs include job IDs, transaction hashes, blocks, and stable error codes; never keys, tokens,
  database/RPC URLs, raw signatures, nonces, or authorization headers.

## Rollback And Recovery

- **Frontend:** redeploy the last known-good Vercel commit; public chain state is unaffected.
- **API:** redeploy the last known-good image only when its schema is compatible with the applied
  migration. Do not downgrade the database destructively.
- **Indexer:** stop all instances, confirm a single replacement, then resume or run the documented
  derived-projection rebuild. Preserve provider, review, registration, proposal, and audit rows.
- **Signer worker:** stop the affected worker, revoke its narrow role if compromise is suspected,
  reconcile receipt/nonce/contract state, rotate/fund a replacement, then resume. Never blindly retry
  an uncertain submission.
- **Provider outage:** retain the last timestamped observation and stop new proposal work.
- **Contract fault:** pause public writes and escalate to the Safe. Existing contracts are not
  upgraded; a new deployment requires a new manifest, ABI/address configuration, and full acceptance.

## Go/No-Go Checklist

- [ ] Supabase backup, revision, and preservation checks recorded.
- [ ] Render web plus exactly three isolated workers healthy.
- [ ] Vercel origin and Render CORS agree.
- [ ] Chain ID, contract, ABI digest, deployment block, roles, VRF, and resolver pool verified.
- [ ] No secrets appear in Git, client variables, logs, screenshots, or CI artifacts.
- [ ] Automated baseline, public reads, and controlled write journeys recorded.
- [ ] Rollback owner and last known-good commit recorded for each service.
- [ ] Known defects have verified fixes or explicit accepted-risk disposition.
