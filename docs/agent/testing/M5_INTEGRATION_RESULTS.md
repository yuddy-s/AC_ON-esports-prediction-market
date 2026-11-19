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

Hosted frontend: https://acon-esports-market.vercel.app (Vercel, M4 Sepolia contracts), built with
`VITE_API_URL=https://ac-on-esports-prediction-market.onrender.com` since November 19; see
[frontend results](M5_FRONTEND_RESULTS.md#hosted-results-vercel--render).

November 19 public check: `https://acon-esports-market.vercel.app` and the free API at
`https://ac-on-esports-prediction-market.onrender.com` are reachable. After credential rotation, a
local one-time indexer advanced the shared checkpoint from safe block 12,163,950 to 12,165,866 in
192 bounded batches. No new contract logs were present and every recorded source, review,
registration, market, trade, event, and position count was preserved. Public smoke then passed
frontend, health, database, CORS, chain, address, deployment block, ABI, freshness (19 seconds), and
two-block lag checks. A second indexer process resumed from the checkpoint, processed one six-block
range, and left all log/projection counts unchanged. See the
[sanitized verification record](../../../deployments/m5-public-2026-11-19/backend-public-verification.json).
Two one-shot registrar starts preserved the confirmed registration and its four audit events. The
second initial proposer start exposed a Supabase transaction-pooler `DuplicatePreparedStatement`
failure. Disabling psycopg automatic preparation fixed it; 33 focused tests and two consecutive
post-fix proposer starts passed without adding intents, events, logs, or transactions. The Render
API restart remains the only incomplete LOC-02 subcheck.

## Automated Baseline

| Layer | Command/check | Environment | Result | Evidence | Notes |
|---|---|---|---|---|---|
| Frontend | Vitest, typecheck, production build | GitHub Actions | pass | PR #64 CI run `44446727316` | Build completed after merging current `dev` changes. |
| Backend | Alembic-compatible SQLite Pytest suite | local + GitHub Actions | 142 passed, 1 PostgreSQL-only local skip; PR #65 CI pending | PR #64 CI plus PR #65 local run | Includes public-smoke, database-target safety, and Supabase pooler regressions. |
| PostgreSQL | migrations, 78-digit values, replay/rebuild/reorg/preservation | disposable CI PostgreSQL 16 | pass | PR #64 PostgreSQL job, CI run `44446727316` | Dedicated validated `TEST_POSTGRES_URL`; never connects to Supabase. |
| Contracts | Foundry unit/fuzz/invariant and six journeys | GitHub Actions / Anvil | pass | PR #64 CI run `44446727316` | Public VRF callback evidence remains separate and pending. |
| Security | Slither, coverage, ABI/runtime and GitGuardian | GitHub Actions | pass | PR #64 CI run `44446727316` | No secret values are copied into this ledger. |
| Browser | Playwright read-only and wallet-failure journeys, plus API-state regressions | local build and public Vercel; hosted Vercel + Render (FE-07) | read-only: local 10/10, public 10/10; full 14-test suite: public 12/14 before the RPC fix (M5-004), 14/14 after it both locally and on the redeployed public site; hosted with strict API checks (status body, six market 0 receipts, API fixture catalog) and 10 mocked regressions: 24/24 twice | [frontend results](M5_FRONTEND_RESULTS.md#hosted-results-vercel--render) | MetaMask writes remain manual. The indexer worker runs on a team machine, so the site can show its stale notice. |

## Public Cross-Layer Acceptance

| ID | Journey/check | Environment | UTC time | Fixture/market | Actor role | Tx/block | Contract result | DB/API result | UI result | Evidence | Status | Defect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PUB-01 | Health, chain/address/ABI and CORS agreement | public Vercel/Render/Supabase plus local indexer | 2026-11-19T03:36:50Z | n/a | operator | n/a | chain/address/block/ABI matched manifest | health/database/CORS pass; safe block 12,165,866, lag 2, age 19 seconds | frontend reachable | [sanitized JSON](../../../deployments/m5-public-2026-11-19/backend-public-verification.json) | pass | — |
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
| LOC-02 | API/indexer/worker restart | local + Supabase staging | resume without duplicate transactions/logs | indexer and empty/confirmed-queue registrar/proposer restart subchecks passed without duplicate rows or transactions; Render API restart pending in [sanitized JSON](../../../deployments/m5-public-2026-11-19/backend-public-verification.json) | pending | M5-003 fixed; API subcheck pending |
| LOC-03 | Duplicate/reordered/missed logs and reorg | Pytest provider | deterministic canonical rebuild | `test_indexer.py` included in 76-test focused pass | pass | — |
| LOC-04 | Uncertain signer submission | mock RPC/gateway | quarantine and reconcile before retry | registration/oracle tests included in 76-test focused pass | pass | — |
| LOC-05 | Seven-day no-proposal timeout | Anvil time control | permissionless resolver selection | pending | pending | — |
| LOC-06 | First-round failure and replacement | Anvil time control | exactly one replacement round | pending | pending | — |
| LOC-07 | Round-two failure and VOID | Anvil time control | VOID and half-value claims | pending | pending | — |
| LOC-08 | Wrong network/rejected/reverted wallet action | browser/manual | clear non-authoritative failure state | Wrong network and rejected request: Playwright with a scripted non-signing wallet, 4/4 on public Vercel and 4/4 on the local build ([frontend results](M5_FRONTEND_RESULTS.md#wallet-failure-journeys-loc-08)). Wrong network also passed manually with MetaMask on the wagmi 3 build (November 19, [manual wallet smoke](M5_FRONTEND_RESULTS.md#manual-wallet-smoke-wagmi-3-pr-63)). Reverted receipt: `tradeStatus` unit tests; manual reverted-receipt run pending. | pass (wrong network, rejection); reverted manual pending | M5-004 found during this run |

## Result Rules

- Use `pass`, `fail`, `blocked`, or `not run`; never use “done” without evidence.
- Link sanitized CI artifacts, Etherscan transactions, screenshots, or repository evidence.
- A public-chain block is not replaced by an Anvil pass; record both separately.
- Link failures to `M5_DEFECT_LOG.md` and update the row only after regression verification.
