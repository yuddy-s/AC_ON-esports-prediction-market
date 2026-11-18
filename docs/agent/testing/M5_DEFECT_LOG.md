# M5 Defect And Fix Ledger

Status: updated November 18, 2026 with Matthew's economics defects. This is the source for the presentation's bugs-found-and-fixed section. See the [economic results report](M5_ECONOMIC_RESULTS.md) for exact amounts and environment limitations.

## Required Fields

| ID | Severity | Environment | Symptom and reproduction | Root cause | Owner | Fix PR/commit | Regression test | Verification | Residual risk | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| M5-001 (ECON-B1) | P2 | Indexer projection; reproduced locally, corrected handler exercised against shared Supabase | Claim cleared wallet positions but left market YES/NO quantities and the position update block stale. Extended lifecycle regression failed before the fix. | Payout projection omitted market quantity subtraction and position block update. | Matthew | [#57](https://github.com/yuddy-s/AC_ON-esports-prediction-market/pull/57), `81850e9` | Three focused indexer tests cover winning/VOID claims, multiple wallets, repeated sync and rebuild; earlier full backend run: 130 passed. | Corrected local handler applied nine missing confirmed events to shared Supabase; zero quantities, claimed flag, exact payout and claim block matched through local API/UI. [Evidence](../../../deployments/m5-economics-2026-11-18/supabase-local-api-verification.json). | Hosted worker rollout and Render/Vercel acceptance remain pending. This is verification of the shared database using a local stack. | verified |
| M5-002 (ECON-B2) | P1 | Local deployment preflight and administration verification | Any positive LINK balance passed funding validation even when below the reviewed VRF reserve. | Checks treated nonzero balance as sufficient funding. | Matthew | [#58](https://github.com/yuddy-s/AC_ON-esports-prediction-market/pull/58), `32ee331` | Six deployment tests include zero configuration, positive-but-insufficient balance, one-unit shortfall and exact-threshold acceptance. | Recorded 120-test local contract run includes six passing deployment tests; source hashes retained in [run metadata](../../../deployments/m5-economics-2026-11-18/run-metadata.json). | Threshold is operator supplied; no automatic reserve estimate or live VRF success is established. Fix is not merged/deployed at this observation; subscriptions remain underfunded. | fixed |

Severity is `P0` release-blocking,
`P1` major journey failure, `P2` degraded/recoverable behavior, or `P3` cosmetic/documentation.
Use `open`, `fixed`, `verified`, `accepted`, or `rejected` as status.

## Verified Pre-M5 Integration Defects

These are valid historical presentation candidates, but do not count as newly discovered M5 bugs.

| ID | Symptom | Root cause and fix | Evidence |
|---|---|---|---|
| HIST-01 | A successful sell remained `MINED` and timed out instead of becoming `INDEXED`. | Frontend polled the legacy buy-only transaction table; polling moved to M4 market history and gained a sell regression test. | PR #47, commit `94b6360`. |
| HIST-02 | Browser reported an indexed API response as unreachable despite HTTP 200. | `localhost` and `127.0.0.1` were treated as different CORS origins; local equivalent origins were accepted and documented. | M4 application runbook and PR #47 integration verification. |
| HIST-03 | Sepolia backfill failed with RPC HTTP 400. | The provider rejected the former 500-block log range; the worker uses a verified 10-block batch. | M4 application runbook. |
| HIST-04 | Portfolio empty/RPC-failure states were ambiguous during rehearsal. | UI state modeling and tests were added so no positions, loading, and RPC failures remain distinct. | Commit `da89232`. |

## Triage Rules

- Record a defect before implementing its fix and link the failing evidence row.
- A fix is not `verified` until its regression test and original environment both pass.
- Contract/API/schema changes require coordinated consumer review; prefer deployment/configuration
  fixes when the frozen interface is correct.
- Never paste secret-bearing logs. Redact wallet ownership details that are not public evidence.
