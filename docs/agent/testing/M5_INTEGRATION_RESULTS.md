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

November 19 final public lifecycle verification (issue #56): **pass**. The complete market 2
on-chain journey is now reconciled with shared Supabase, the public Render API, and the
actual Vercel market page. All 22 market events match the database; the 21 trade/resolution/
claim events and three claimed positions match the public APIs. The hosted page shows final
YES, the five-member committee, 3 YES / 2 NO votes, zero outstanding shares and collateral,
and the five indexed trades. Initial catch-up processed 17 confirmed logs; repeat runs added
none. Final recorded safe block: 12,169,477. See the
[final cross-layer record](../../../deployments/m5-sepolia-lifecycle-2026-11-19/cross-layer/README.md)
for exact accounting, API responses, sync preservation, independent result-source review,
and the hosted screenshot. Public UI acceptance was read-only; holder-specific connected
portfolio screens and the separate MetaMask domain classification were not exercised.

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
| PUB-02 | Reviewed fixture registration | Sepolia/public stack | 2026-11-19T06:14:48Z | fixture 566 KeepBest Gaming vs A Team (key `0xe682…647c`, start 08:30Z) | user + registrar | [`0x99963bd5…bff9`](https://sepolia.etherscan.io/tx/0x99963bd521123bc165c928870f717cd72a7b1620392e888cda01a48f0ab7bff9) block 12166634 | `getFixture` registered=true, registrar `0xFfb7…edaa` | catalog `registration_request_status: confirmed` | fixture catalog lists the confirmed fixture | [lifecycle run record](../../../deployments/m5-sepolia-lifecycle-2026-11-19/README.md#pub-02--reviewed-fixture-registration-confirmed) | pass | — |
| PUB-03 | User-funded market creation | Sepolia/public stack | 2026-11-19T06:21:12Z | market 2, fixture 566, deadline 08:15Z (start − 15 min) | creator `0xB5ce…9A6A` | [`0x196bd00e…db58`](https://sepolia.etherscan.io/tx/0x196bd00ebf74f5e197f67efba354b29bfa0545add3ffaba2c85344c0b0e4db58) block 12166666 | subsidy 34.657359027997265471 ACON escrowed; `marketCount` 2→3 | indexed market 2 present with creation data | hosted site lists market 2 | [lifecycle run record](../../../deployments/m5-sepolia-lifecycle-2026-11-19/README.md#pub-03--user-funded-market-creation-confirmed) | pass | — |
| PUB-04 | Guarded buy and indexed position | Sepolia/public stack | 2026-11-19T06:22:12Z / 06:22:48Z; further buys 07:50:12Z / 07:52:48Z | market 2 | traders `0xB5ce…9A6A`, `0x6a51…ffaCc`, `0xcddb…15A8C` | [`0xc1f9a796…93c`](https://sepolia.etherscan.io/tx/0xc1f9a79614833b6a3787150f5c6684853b4ac6a9c18f29daaa0d5ae3bc75193c) b12166671; [`0xb250577e…9b9`](https://sepolia.etherscan.io/tx/0xb250577eedd814b83bcb2081db3738423aad693a765337c4e97fb133a92cb9b9) b12166674; [`0x874844b3…09b59`](https://sepolia.etherscan.io/tx/0x874844b3b8b9e86eb5736e23b03635d084e245a3f67bcc518f30acb2ec209b59) b12167081; [`0x0d6cbe38…a29f4`](https://sepolia.etherscan.io/tx/0x0d6cbe38914869505df89d10f56483f14467be192d1f5221b5dfd647e75a29f4) b12167093 | 38 YES / 11 NO outstanding; collateral 60.958136813544678246 ACON reconciles exactly | `/api/v2/markets/2` OPEN with exact quantities; history lists the buys at exact base-unit amounts | hosted market page shows market 2 | [lifecycle run record](../../../deployments/m5-sepolia-lifecycle-2026-11-19/README.md#pub-04--guarded-buys-and-indexed-position-confirmed) | pass | — |
| PUB-05 | Guarded sell and proceeds | Sepolia/public stack | 2026-11-19T07:59:24Z | market 2 | seller `0xB5ce…9A6A` | [`0x187b919a…e3c`](https://sepolia.etherscan.io/tx/0x187b919ab754c1d51d57515e590955a9f4885cc5c933669a497389a8db4d2e3c) block 12167125 | 10 YES sold for 6.081731240803238806 ACON via the guarded `quoteSell` path; quantities 38→28 YES; collateral delta exact (60.958136813544678246 → 54.876405572741439440) | `/api/v2/markets/2/history` lists the SELL with exact base-unit proceeds | hosted market page position updated | [lifecycle run record](../../../deployments/m5-sepolia-lifecycle-2026-11-19/README.md#pub-05--guarded-sell-and-proceeds-confirmed) | pass | — |
| PUB-06 | Reviewed proposal and bonded challenge | Sepolia/public stack | proposal 2026-11-19T15:07:36Z; challenge 2026-11-19T15:12:12Z | market 2 | proposer `0x137F…0Df`; challenger R01 `0x6a51…ffaCc` | proposal [`0x9ca27bfb…1d06`](https://sepolia.etherscan.io/tx/0x9ca27bfbf88d685ac0dcc6d2f5d48c73d4bde665352a66cae5902b30ff861d06) block 12169177; challenge [`0x7c0ddbe4…743`](https://sepolia.etherscan.io/tx/0x7c0ddbe44de2174b6952b63b4e115ceccac9c1dcc66fb66bd6ae3afd0df6b743) block 12169199 | deliberately incorrect NO proposal for the dispute-path test; true result KeepBest 2–0 (YES); valid challenge escrowed 10 ACON, moved market PROPOSED → DISPUTED, and left market collateral unchanged | proposal and challenge payloads/receipts match DB and public resolution API; 10 ACON bond recorded | hosted page shows NO proposal and challenger with 10 ACON bond | [final cross-layer evidence](../../../deployments/m5-sepolia-lifecycle-2026-11-19/cross-layer/README.md) | pass | — |
| PUB-07 | Real VRF request/callback and five-member committee | Sepolia/public stack | request 15:12:48Z; callback 15:13:48Z (2026-11-19) | market 2, round 1 | caller R01 (permissionless); Chainlink VRF | request [`0x095e5358…4e35`](https://sepolia.etherscan.io/tx/0x095e53589a5cd579fc4d9b67f9afb7fda78e506853465aafa3a56b3be3374e35) block 12169201; callback [`0x90e45813…5d22`](https://sepolia.etherscan.io/tx/0x90e45813aefe950558afa346389a3dbe7267e959dbdec045a0155ed23bc75d22) block 12169206 | real VRF v2.5 request ID `64454812201355125149715950417696302771148563436230064546743731846367863751153` fulfilled in ~60 s; five-member committee R05/R09/R04/R08/R03 from the frozen 8-candidate pool; escrow 390.20 → 390.189642 LINK | request ID, callback and five-member committee match DB and public resolution API | hosted page shows round 1 and all five selected committee addresses | [final cross-layer evidence](../../../deployments/m5-sepolia-lifecycle-2026-11-19/cross-layer/README.md) | pass | — |
| PUB-08 | Three matching resolver votes and settlement | Sepolia/public stack | 2026-11-19T15:19:36Z–15:21:48Z | market 2 | committee R04/R05/R08/R03/R09 | R04 YES [`0x2a342ac0…dc07`](https://sepolia.etherscan.io/tx/0x2a342ac0b55678d5bbf03638b4db1ba20015ec06904035a4f8876a19611adc07); R05 YES [`0x0456e179…fc99`](https://sepolia.etherscan.io/tx/0x0456e179063a313347c0b7550e3cd91f9737fbf0c88f18d28dddc6c806edfc99); R03 NO [`0x5bae24a9…1def`](https://sepolia.etherscan.io/tx/0x5bae24a960a1102e4bf51abbd2b4b8410dc2328d4479518070e69dd527091def); R09 NO [`0x4f69e3a9…b12`](https://sepolia.etherscan.io/tx/0x4f69e3a952493a01873d12731df2d6a9d9b863f133238feabd5588274c0f7b12); settling R08 YES [`0x4da4c265…f701`](https://sepolia.etherscan.io/tx/0x4da4c26583dfa90a57aec8a347beb70c4de24db7762a592ef2fc1192bfd3f701) | scripted divided committee (3 YES / 2 NO, labeled); third matching vote settled → FINALIZED, outcome YES (true 2–0 result, overturning the deliberate NO proposal); bond refunded to challenger | five eligible votes, final YES and bond refund match DB and public resolution API | hosted page shows FINAL: YES / FINALIZED and votes YES 3 / NO 2 / VOID 0 | [final cross-layer evidence](../../../deployments/m5-sepolia-lifecycle-2026-11-19/cross-layer/README.md) | pass | — |
| PUB-09 | Payout and duplicate-claim rejection | Sepolia/public stack | 2026-11-19T15:22:48Z / 15:23:00Z / 15:23:24Z | market 2 | holders `0xB5ce…9A6A`, R01, R02 | Benny [`0xda3f38f4…004a`](https://sepolia.etherscan.io/tx/0xda3f38f438f5053bdccf2da5b9e659f9efc485cfdbbf1a02061b5611525004a4); R01 [`0x256772e1…e92`](https://sepolia.etherscan.io/tx/0x256772e1aa887d1e4f2060574161b4b54480ccf415980c64395609ebf0108e92); R02 [`0x85f33a8c…cf24`](https://sepolia.etherscan.io/tx/0x85f33a8c5ebc00cbbf8a1ee45c30a704831b8d34a5f5bbaf51cddd680961cf24) | 17 ACON + 11 ACON winning payouts; losing close-out paid 0; duplicate `claimPayout` reverts `AlreadyClaimed`; wallet deltas exact | all three positions claimed with zero shares; payouts 17 / 11 / 0 ACON and claim blocks match public portfolio and claims APIs | hosted page shows final YES and zero outstanding shares; holder-wallet portfolio screens not exercised | [final cross-layer evidence](../../../deployments/m5-sepolia-lifecycle-2026-11-19/cross-layer/README.md) | pass | — |
| PUB-10 | Bond, remaining-liability and creator-surplus reconciliation | Sepolia/public stack | 2026-11-19T15:23:48Z | market 2 | creator `0xB5ce…9A6A`; challenger bond automatic | [`0x94460bde…a3a`](https://sepolia.etherscan.io/tx/0x94460bdec7b3d6416a21397ee6b6c92845e2621b70c4aafe1f680ff762da0a3a) block 12169256 | changed-outcome bond refunded to challenger (exact pre-challenge balance); surplus 26.876405572741439440 = collateral − 28 liability, withdrawn; market collateral 0 | exact bond refund and surplus events match DB/API; last claim liability zero; receipt/contract accounting exact | hosted page shows zero collateral and zero outstanding shares | [final cross-layer evidence](../../../deployments/m5-sepolia-lifecycle-2026-11-19/cross-layer/README.md) | pass | — |

Note (2026-11-19): an earlier guarded-sell journey with quote-equals-proceeds and all eight
  reconciliation checks true exists from the M4-era trading (tx
  [`0x6906d816…96e0f0`](https://sepolia.etherscan.io/tx/0x6906d816e7e0ab2f6fbac6a84018817d790b98a6c925ccaadb1b4ce18696e0f0),
  see [economic results](M5_ECONOMIC_RESULTS.md)). R01 and R02 traded on market 2 and are
  contract-excluded from its committee; the eligible pool is R03–R10 (eight wallets).


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
