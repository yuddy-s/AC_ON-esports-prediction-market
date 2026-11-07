# M5 Defect And Fix Ledger

Status: draft. This is the source for the presentation's bugs-found-and-fixed section.

## Required Fields

| ID | Severity | Environment | Symptom and reproduction | Root cause | Owner | Fix PR/commit | Regression test | Verification | Residual risk | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| M5-001 | pending | pending | pending | pending | pending | pending | pending | pending | pending | open |

Remove the placeholder after the first M5 defect is recorded. Severity is `P0` release-blocking,
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
