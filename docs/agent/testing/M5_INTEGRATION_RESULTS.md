# M5 Integration Results

Status: draft evidence ledger. Add results only after the named environment was exercised.
Never include credentials, private keys, raw signatures, tokens, database URLs, or secret-bearing logs.

November 18 update: Matthew's [economic results and receipt reconciliation](M5_ECONOMIC_RESULTS.md)
record 120 local contract tests, five public buys and one sell, and the existing market 0
VOID bond/payout/surplus journey. Shared Supabase and the local API/UI now agree after confirmed
event catch-up with the #57 handler. These are dated local-stack subchecks of the hosted public
acceptance rows below; hosted Render/Vercel verification remains pending. The
[VRF recheck](../../../deployments/sepolia-2026-11-17-vrf-diagnostic/RECHECK-2026-11-18.md)
still shows no successful callback, committee or votes, so issue #56 remains open. Local test
results do not replace the pending CI rows below.

November 19 public check: `https://acon-esports-market.vercel.app` and the free API at
`https://ac-on-esports-prediction-market.onrender.com` are reachable. `/health` reported an
available database. The public smoke passed frontend, health, CORS, chain, address, deployment
block, ABI, and two-block lag checks, then correctly failed freshness: the last local indexer update
was `2026-11-18T21:01:05.673906Z` (23,266 seconds old at the check). This is partial public-stack
evidence, not a passing PUB-01 result; rerun after the exposed database credential is rotated and
one local indexer catch-up completes.

## Automated Baseline

| Layer | Command/check | Environment | Result | Evidence | Notes |
|---|---|---|---|---|---|
| Frontend | Vitest, typecheck, production build | GitHub Actions | pass | PR #64 CI run `44446727316` | Build completed after merging current `dev` changes. |
| Backend | Alembic-compatible SQLite Pytest suite | local + GitHub Actions | 139 passed, 1 PostgreSQL-only local skip; CI pass | PR #64 commit `0d34132`, CI run `44446727316` | Includes public-smoke and database-target safety regressions. |
| PostgreSQL | migrations, 78-digit values, replay/rebuild/reorg/preservation | disposable CI PostgreSQL 16 | pass | PR #64 PostgreSQL job, CI run `44446727316` | Dedicated validated `TEST_POSTGRES_URL`; never connects to Supabase. |
| Contracts | Foundry unit/fuzz/invariant and six journeys | GitHub Actions / Anvil | pass | PR #64 CI run `44446727316` | Public VRF callback evidence remains separate and pending. |
| Security | Slither, coverage, ABI/runtime and GitGuardian | GitHub Actions | pass | PR #64 CI run `44446727316` | No secret values are copied into this ledger. |
| Browser | Playwright read-only journeys | public Vercel/Render | pending implementation | pending trace/screenshots | MetaMask writes remain manual. |

## Public Cross-Layer Acceptance

| ID | Journey/check | Environment | UTC time | Fixture/market | Actor role | Tx/block | Contract result | DB/API result | UI result | Evidence | Status | Defect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PUB-01 | Health, chain/address/ABI and CORS agreement | public Vercel/Render/Supabase plus local indexer | 2026-11-19 | n/a | operator | n/a | n/a | health/database/CORS/config pass; freshness failed at 23,266 seconds old despite two-block stored lag | frontend reachable | public URLs and smoke output; sanitized artifact pending | blocked | local indexer catch-up pending after credential rotation |
| PUB-02 | Reviewed fixture registration | Sepolia/public stack | pending | pending | user + registrar | pending | pending | pending | pending | pending | pending | — |
| PUB-03 | User-funded market creation | Sepolia/public stack | pending | pending | creator | pending | pending | pending | pending | pending | pending | — |
| PUB-04 | Guarded buy and indexed position | Sepolia/public stack | pending | pending | trader | pending | pending | pending | pending | pending | pending | — |
| PUB-05 | Guarded sell and proceeds | Sepolia/public stack | pending | pending | trader | pending | pending | pending | pending | pending | pending | — |
| PUB-06 | Reviewed proposal and bonded challenge | Sepolia/public stack | pending | pending | proposer + challenger | pending | pending | pending | pending | pending | pending | — |
| PUB-07 | Real VRF request/callback and five-member committee | Sepolia/public stack | pending | pending | caller + VRF | pending | pending | pending | pending | pending | pending | — |
| PUB-08 | Three matching resolver votes and settlement | Sepolia/public stack | pending | pending | resolvers | pending | pending | pending | pending | pending | pending | — |
| PUB-09 | Payout and duplicate-claim rejection | Sepolia/public stack | pending | pending | position holder | pending | pending | pending | pending | pending | pending | — |
| PUB-10 | Bond, remaining-liability and creator-surplus reconciliation | Sepolia/public stack | pending | pending | challenger/creator | pending | pending | pending | pending | pending | pending | — |

## Local Failure And Time-Controlled Acceptance

| ID | Scenario | Environment | Expected result | Evidence | Status | Defect |
|---|---|---|---|---|---|---|
| LOC-01 | Provider 429/outage/malformed response | deterministic transport | retain last observation and stop proposal work | `test_pandascore.py` included in 76-test focused pass | pass | — |
| LOC-02 | API/indexer/worker restart | local + Supabase staging | resume without duplicate transactions/logs | pending | pending | — |
| LOC-03 | Duplicate/reordered/missed logs and reorg | Pytest provider | deterministic canonical rebuild | `test_indexer.py` included in 76-test focused pass | pass | — |
| LOC-04 | Uncertain signer submission | mock RPC/gateway | quarantine and reconcile before retry | registration/oracle tests included in 76-test focused pass | pass | — |
| LOC-05 | Seven-day no-proposal timeout | Anvil time control | permissionless resolver selection | pending | pending | — |
| LOC-06 | First-round failure and replacement | Anvil time control | exactly one replacement round | pending | pending | — |
| LOC-07 | Round-two failure and VOID | Anvil time control | VOID and half-value claims | pending | pending | — |
| LOC-08 | Wrong network/rejected/reverted wallet action | browser/manual | clear non-authoritative failure state | pending | pending | — |

## Result Rules

- Use `pass`, `fail`, `blocked`, or `not run`; never use “done” without evidence.
- Link sanitized CI artifacts, Etherscan transactions, screenshots, or repository evidence.
- A public-chain block is not replaced by an Anvil pass; record both separately.
- Link failures to `M5_DEFECT_LOG.md` and update the row only after regression verification.
