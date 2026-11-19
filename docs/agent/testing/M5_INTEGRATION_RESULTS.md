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

Hosted frontend: https://acon-esports-market.vercel.app (Vercel, M4 Sepolia contracts). It reads
contracts only until the Render API URL is configured as `VITE_API_URL`; see
[frontend results](M5_FRONTEND_RESULTS.md).

## Automated Baseline

| Layer | Command/check | Environment | Result | Evidence | Notes |
|---|---|---|---|---|---|
| Frontend | Vitest, typecheck, production build | GitHub Actions | pending M5 rerun | pending CI link | M4 local baseline was 159 Vitest tests. |
| Backend | Alembic upgrade and Pytest | GitHub Actions / SQLite | pending M5 rerun | pending CI link | M4 documented baseline was 129 tests. |
| PostgreSQL | migrations, 78-digit values, replay/rebuild | CI PostgreSQL service | pending implementation | pending | SQLite remains the fast unit path. |
| Contracts | Foundry unit/fuzz/invariant and six journeys | GitHub Actions / Anvil | pending M5 rerun | pending CI/artifact | Record exact test summary. |
| Security | Slither, coverage, ABI/runtime and GitGuardian | GitHub Actions | pending M5 rerun | pending CI/artifact | Do not copy secret scanner payloads. |
| Browser | Playwright read-only and wallet-failure journeys | local build and public Vercel (contract reads only); Render pending | read-only: local 10/10, public 10/10; full 14-test suite: public 12/14 before the RPC fix (M5-004), local 14/14 after; with API pending | [frontend results](M5_FRONTEND_RESULTS.md) | MetaMask writes remain manual. |

## Public Cross-Layer Acceptance

| ID | Journey/check | Environment | UTC time | Fixture/market | Actor role | Tx/block | Contract result | DB/API result | UI result | Evidence | Status | Defect |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PUB-01 | Health, chain/address/ABI and CORS agreement | public stack | pending | n/a | operator | n/a | n/a | pending | pending | pending | pending | — |
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
| LOC-01 | Provider 429/outage/malformed response | deterministic transport | retain last observation and stop proposal work | pending | pending | — |
| LOC-02 | API/indexer/worker restart | local + Supabase staging | resume without duplicate transactions/logs | pending | pending | — |
| LOC-03 | Duplicate/reordered/missed logs and reorg | Pytest provider | deterministic canonical rebuild | pending | pending | — |
| LOC-04 | Uncertain signer submission | mock RPC/gateway | quarantine and reconcile before retry | pending | pending | — |
| LOC-05 | Seven-day no-proposal timeout | Anvil time control | permissionless resolver selection | pending | pending | — |
| LOC-06 | First-round failure and replacement | Anvil time control | exactly one replacement round | pending | pending | — |
| LOC-07 | Round-two failure and VOID | Anvil time control | VOID and half-value claims | pending | pending | — |
| LOC-08 | Wrong network/rejected/reverted wallet action | browser/manual | clear non-authoritative failure state | Wrong network and rejected request: Playwright with a scripted non-signing wallet, 4/4 on public Vercel and 4/4 on the local build ([frontend results](M5_FRONTEND_RESULTS.md#wallet-failure-journeys-loc-08)). Reverted receipt: `tradeStatus` unit tests; manual MetaMask run pending. | pass (wrong network, rejection); reverted manual pending | M5-004 found during this run |

## Result Rules

- Use `pass`, `fail`, `blocked`, or `not run`; never use “done” without evidence.
- Link sanitized CI artifacts, Etherscan transactions, screenshots, or repository evidence.
- A public-chain block is not replaced by an Anvil pass; record both separately.
- Link failures to `M5_DEFECT_LOG.md` and update the row only after regression verification.
