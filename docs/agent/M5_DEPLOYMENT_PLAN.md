# M5 Public Deployment And Rollback Plan

Status: public Vercel frontend and free Render API deployed. The team selected local operator-run
indexer/registrar/proposer processes instead of paid hosted workers. The full Sepolia lifecycle —
reviewed fixture, market creation, trades, proposal, bonded challenge, a **real fulfilled VRF
committee draw, votes, settlement, claims and surplus** — is recorded on-chain in
[deployments/m5-sepolia-lifecycle-2026-11-19](../../deployments/m5-sepolia-lifecycle-2026-11-19/README.md).
Remaining acceptance: the indexed DB/API/UI reflection of the settled market (the operator
indexer resumes and catches up), the hosted Render/Vercel verification (ECON-05), and the
LOC-02 Render API restart subcheck.

## Target Topology

```text
Browser / MetaMask
  -> Vercel static frontend
       -> Render FastAPI web service
            -> Supabase PostgreSQL
       -> Ethereum Sepolia RPC / M4 contracts

Local indexer process (exactly one) -> Sepolia logs -> Supabase projections
Local registrar process             -> approved jobs -> Sepolia registrar role
Local proposer process              -> reviewed intents -> Sepolia proposer role
Operator-only PandaScore import/review -> Supabase source and audit rows
```

The Safe owns administration and the VRF subscription. Safe-owner and resolver keys are never
hosted. Local signers use separate least-privilege accounts. Contracts remain authoritative.

## Configuration Ownership

| Location | Public values | Secret values | Owner |
|---|---|---|---|
| Vercel | chain ID, contract/token addresses, Render API URL | none | Adriel |
| Render web | chain ID and exact Vercel origin | database URL | Yudhveer |
| Local indexer | chain/address/deployment block, ABI path, confirmation depth | database URL, RPC URL | Yudhveer |
| Local registrar | public contract configuration | database, RPC, registrar key | Yudhveer |
| Local proposer | public contract configuration | database, RPC, proposer key | Yudhveer |
| Operator environment | provider selection | PandaScore token and review access | Yudhveer |
| Team custody | Safe/VRF/resolver public configuration | Safe-owner and resolver keys | Benny/team; never hosted |

Use the post-setup manifest and frozen ABI in `deployments/sepolia-2026-11-02`. Configure the
exact Vercel origin in backend CORS. Keep indexer confirmation depth at two and the verified RPC
batch size at ten unless a new provider is tested.

## Deployment Order

1. Rotate the exposed disposable challenger wallet; verify Git ignore and secret scanning.
2. Back up Supabase and record table counts plus current Alembic revision.
3. Apply `alembic upgrade head`; verify revision `20261102_0008` and preserved counts.
4. Deploy the free Render web service and verify `/health` without exposing configuration.
5. Start exactly one local indexer; verify chain/address/ABI, safe-block advancement, recent update
   time, and acceptable block lag through the public API.
6. After verifying roles, balances, and pending work, start the separate local registrar/proposer
   only for their intended jobs.
7. Deploy Vercel with the public Render URL and exact Sepolia addresses.
8. Run public smoke and Playwright reads, then controlled MetaMask acceptance transactions.
9. Record sanitized results in the integration ledger before declaring the release healthy.
10. Stop proposer and registrar immediately after their evidence is complete, then stop the indexer
    after its final safe block is recorded. Leave the free API deployed.

The root `render.yaml` remains a reviewed reference for an optional paid-worker deployment. It is
not synced for the cost-constrained M5 deployment. The actual free API is created as a standalone
Render web service; no signer key or provider token is hosted there.

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
- **Contract fault:** suspend team-operated frontend and signer writes, warn users about the
  affected chain/address, and escalate to the Safe. This does not freeze direct contract calls.
  Existing contracts are not upgraded; a new deployment requires a new manifest, ABI/address
  configuration, and full acceptance.

### Contract rollback criteria

Contracts are immutable, so a contract rollback never reverts bytecode in place. It means leaving
the current deployment at its recorded state and moving public activity to a fresh deployment with
a new versioned manifest. Any one of the following triggers a rollback review:

- A demonstrated or reported defect that can lose or misdirect funds (pricing, payout, surplus, or
  bond accounting).
- Compromise of a Safe owner key, or exposure of a role key whose damage cannot be contained by
  revoking that role through the Safe.
- VRF fulfillment permanently impossible on the deployed immutable configuration (deprecated gas
  lane or key hash, discontinued LINK billing, or a coordinator limit incompatible with the frozen
  2,000,000 callback gas), evidenced by the diagnostic records and, where possible, Chainlink
  communication.
- Deployed bytecode no longer matching the frozen ABI/source records in
  `deployments/sepolia-2026-11-02`, or an unexplained coordinator/subscription ownership change.

Repair these without redeploying instead:

- Frontend, API, indexer, or database defects (service redeploy or derived-projection rebuild).
- An underfunded VRF subscription (fund to the reviewed minimum; the merged preflight rejects
  balances below it).
- Stale, duplicate, or superseded VRF requests (the contract ignores them; retry and advance
  paths exist).
- Non-admin key exposure with revocable roles (rotate through the Safe, then resume).

Contain team-operated writes first:

- Adriel deploys a read-only/maintenance frontend with transaction controls disabled, or withdraws
  the public frontend until that release is ready. Display a notice identifying the affected
  chain and contract address.
- Yudhveer stops the registrar and proposer workers. The indexer may keep reading if its
  configuration and database remain trusted.
- The Safe revokes exposed operational roles and rotates service accounts where it still has
  trusted administrative control.

These are off-chain service controls and narrow role changes, not a global on-chain pause.
The deployed `PredictionMarket` has no contract-wide pause function: users can still submit
`buy`, `sell`, and other permitted calls directly or through another frontend. Stopping workers
or changing the public site's contract address does not block those calls. The Safe cannot
rewrite positions, prices, payouts, or confirmed transactions.

If the incident requires stopping trades on an affected OPEN market, a registrar can call
`closeTrading` with a nonzero evidence hash before its deadline. This is an irreversible market
closure, not a temporary pause: it shortens the stored deadline to the close time, starts the
deadline-based proposal/timeout timing from that value, and the market cannot be reopened.
Use it only as an explicitly recorded Safe incident decision, with the market IDs, evidence,
old/new deadlines and receipts. Closing does not immediately settle or refund positions;
resolution and claims continue under the existing contract rules.

Classify the defect as blocker (funds loss or compromise), degraded (functionality unavailable),
or cosmetic, and record the trusted Safe decision (2/3) with evidence links. Then choose
accept-and-mitigate, redeploy the same source with changed configuration, or redeploy changed
source. If a trusted Safe quorum is unavailable, keep team-operated writes suspended and resolve
trusted administration for a replacement before releasing it. Rollback owner for contracts: Benny.

If a rollback proceeds: snapshot the state evidence (manifest, receipts, final block), deploy from
reviewed source per `docs/agent/CONTRACT_DEPLOYMENT.md`, rerun the Safe setup and the six-argument
`VerifyAdministration.verify`, publish a new versioned manifest and ABI, update Vercel, Render, and
local-worker configuration, and rerun full acceptance before team-operated writes resume. Positions
do not migrate: claims and creator surplus on the old address remain claimable there under contract rules,
and the old manifest stays the record for that deployment.

Last known-good contract record: `deployments/sepolia-2026-11-02` (deployed source `721a6fe`,
PredictionMarket `0x03ae48f0…10E9`).

## Go/No-Go Checklist

- [ ] Supabase backup, revision, and preservation checks recorded.
- [x] Optional Render Blueprint defines the reviewed paid topology without secret values.
- [x] Public free Render API and Vercel frontend are reachable and share Supabase data.
- [x] Public smoke tooling validates health, CORS, chain/address/block/ABI and freshness.
- [x] Exactly one local indexer was current during the recorded public evidence window.
- [ ] Separate local registrar/proposer processes complete intended jobs without duplicates.
- [x] Vercel origin and Render CORS agree.
- [ ] Chain ID, contract, ABI digest, deployment block, roles, VRF, and resolver pool verified.
- [ ] No secrets appear in Git, client variables, logs, screenshots, or CI artifacts.
- [ ] Automated baseline, public reads, and controlled write journeys recorded.
- [ ] Rollback owner and last known-good commit recorded for each service.
- [ ] Known defects have verified fixes or explicit accepted-risk disposition.
