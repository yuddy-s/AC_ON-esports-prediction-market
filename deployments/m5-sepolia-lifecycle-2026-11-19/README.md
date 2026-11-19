# M5 Sepolia Lifecycle Run — November 19, 2026

Live Sepolia evidence for issue #56: a reviewed fixture registered, a user-funded market
created, guarded trades executed, and the real VRF-to-settlement journey completed on-chain.
Post-trading DB/API/UI verification remains pending the operator indexer catch-up.
Every hash below links to Sepolia Etherscan. This record is the handoff source for the
`PUB-02`–`PUB-10` rows in `docs/agent/testing/M5_INTEGRATION_RESULTS.md`; local Anvil
evidence (LOC-05/06/07) stays separately labeled and does not substitute for this record.

Environment: chain 11155111, PredictionMarket `0x03ae48f03C7822540a91DA2168602bd49dC510E9`,
ACONTestToken `0xf85b2278a810410c6AE0b7490d34671E0C8e6E90`, coordinator
`0x9DdfaCa8183c41ad55329BdeeD9F6A8d53168B1B`, subscription
`43360769431604264970977939572487330506316889248276568284147859733693920197182`,
Safe `0xE33DDf0E7224245efe3D6BFcb39A78C22fbbAaac`. Deployed source `721a6fe`.

## Roles (this run)

| Role | Wallet | Note |
|---|---|---|
| Creator + trader A | `0xB5ce8428DD6cB9FEfD54282CB49Ef7d2629d9A6A` | deployment/Safe-owner wallet |
| Challenger + trader B | one of the ten resolver wallets (R01) | excluded from committee by `_notConflicted` (challenger + trader) |
| Proposer | `0x137F79Cc7eA5c59Fa66bc09351b5f9331225c0Df` | granted `PROPOSER_ROLE` via Safe |
| Registrar | `0xFfb7c2D7B39A3da503Ef30761CCD1B19B767eDaa` | granted `REGISTRAR_ROLE` via Safe |
| Committee pool | remaining eligible resolver wallets | three matching votes settle |

## PUB-02 — Reviewed fixture registration (confirmed)

Fixture 566: **KeepBest Gaming vs A Team**, valorant, provider `pandascore`,
external match `1805897`, scheduled start **2026-11-19T08:30:00Z**.

- Backend catalog: `registration_request_status: "confirmed"` (operator-reviewed evidence,
  registrar worker submitted).
- Fixture key: `0xe6824a454577ad2b6ed1a46889654652bedca08f3e46c4c83fb6d88e3f3e647c`
- On-chain: `getFixture(key)` → `registered: true`, `hasMarket: false` at read time,
  registrar `0xFfb7c2D7B39A3da503Ef30761CCD1B19B767eDaa`.
- Tx: [`0x99963bd521123bc165c928870f717cd72a7b1620392e888cda01a48f0ab7bff9`](https://sepolia.etherscan.io/tx/0x99963bd521123bc165c928870f717cd72a7b1620392e888cda01a48f0ab7bff9)
  block 12166634, log 295 (`FixtureRegistered`).

## PUB-03 — User-funded market creation (confirmed)

- Market 2: "Will KeepBest Gaming beat A Team?" (`marketCount` 2 → 3).
- Deadline **2026-11-19T08:15:00Z** — exactly 15 minutes before the scheduled start (the
  contract maximum), strictly in the future at creation.
- Subsidy `34.657359027997265471` ACON escrowed from the creator.
- Tx: [`0x196bd00ebf74f5e197f67efba354b29bfa0545add3ffaba2c85344c0b0e4db58`](https://sepolia.etherscan.io/tx/0x196bd00ebf74f5e197f67efba354b29bfa0545add3ffaba2c85344c0b0e4db58)
  block 12166666, log 23 (`MarketCreated`, creator `0xB5ce…9A6A`).
- Negative evidence (pending, before the trading deadline): duplicate `createMarket` on the
  same fixture reverts `MarketAlreadyExists` (read-only `eth_call`).

## PUB-04 — Guarded buys and indexed position (confirmed)

| Trade | Trader | Outcome | Shares | Cost (ACON) | Tx | Block |
|---|---|---|---|---|---|---|
| 1 | `0xB5ce…9A6A` | YES | 10 | 5.249584441082326514 | [`0xc1f9a796…93c`](https://sepolia.etherscan.io/tx/0xc1f9a79614833b6a3787150f5c6684853b4ac6a9c18f29daaa0d5ae3bc75193c) | 12166671 |
| 2 | `0xB5ce…9A6A` | YES | 17 | 10.051193344465086260 | [`0xb250577e…9b9`](https://sepolia.etherscan.io/tx/0xb250577eedd814b83bcb2081db3738423aad693a765337c4e97fb133a92cb9b9) | 12166674 |
| 3 | `0x6a51…ffaCc` (R01) | YES | 11 | 7.225546927180017441 | [`0x874844b3…09b59`](https://sepolia.etherscan.io/tx/0x874844b3b8b9e86eb5736e23b03635d084e245a3f67bcc518f30acb2ec209b59) | 12167081 |
| 4 | `0xcddb…15A8C` (R02) | NO | 11 | 3.774453072819982560 | [`0x0d6cbe38…a29f4`](https://sepolia.etherscan.io/tx/0x0d6cbe38914869505df89d10f56483f14467be192d1f5221b5dfd647e75a29f4) | 12167093 |

- On-chain state reconciles: 38 YES / 11 NO outstanding, collateral `60.958136813544678246` =
  subsidy 34.657359027997265471 + buys 26.300777785547412775
  (5.249584441082326514 + 10.051193344465086260 + 7.225546927180017441 + 3.774453072819982560).
- **Committee-eligibility consequence:** R01 (challenger + trader) and R02 (trader/holder) are
  excluded from selection for this market by `_notConflicted`. The eligible pool is R03–R10
  (eight wallets) — above the five needed to freeze the snapshot. No further resolver wallets
  may trade on market 2, or selection would fail with `ResolverSelectionPending`.
- Indexed reflection: `GET /api/v2/markets/2` returns `state: OPEN` with exact quantities and
  deadline `2026-11-19T08:15:00Z`; `/api/v2/markets/2/history` lists the trades with exact
  base-unit amounts. (The market row's `source_transaction_hash` reflects the latest projecting
  event; the creation tx above is the authoritative creation record.)

## PUB-05 — Guarded sell and proceeds (confirmed)

- Sell executed at **2026-11-19T07:59:24Z** (16 minutes before the trading deadline):
  **10 YES sold for 6.081731240803238806 ACON** by `0xB5ce…9A6A` via the guarded frontend
  sell path (`quoteSell` minimum-return guard applied before submission).
- Tx: [`0x187b919a…e3c`](https://sepolia.etherscan.io/tx/0x187b919ab754c1d51d57515e590955a9f4885cc5c933669a497389a8db4d2e3c)
  block 12167125, log 1 (`SellExecuted`).
- On-chain reconciliation: quantities 38→28 YES (11 NO unchanged), collateral
  `60.958136813544678246 − 6.081731240803238806 = 54.876405572741439440` — exact.
- Indexed reflection: `/api/v2/markets/2/history` lists the SELL with the exact base-unit
  proceeds at block 12167125.
- Complementary guarded-sell evidence with quote-equals-proceeds and all eight reconciliation
  checks true exists from the M4-era public trading (0.01 YES, quote `0.001192323234939916` ==
  received, guard `1180400002590516` honored, tx
  [`0x6906d816…96e0f0`](https://sepolia.etherscan.io/tx/0x6906d816e7e0ab2f6fbac6a84018817d790b98a6c925ccaadb1b4ce18696e0f0)
  block 12052699); see [M5_ECONOMIC_RESULTS.md](../../docs/agent/testing/M5_ECONOMIC_RESULTS.md).

## PUB-06 / PUB-07 — Proposal, bonded challenge, real VRF

### PUB-06a — Result proposal (confirmed, deliberately incorrect outcome — dispute-path test)

The true match result is **KeepBest Gaming 2–0 A Team (YES)**, verified against the evidence
source below. The team submitted a **deliberately incorrect proposal (NO)** to exercise the
dispute-and-overturn path end to end; the resolver committee is expected to correct the
outcome to the true result, which is also what the final settled state must show.

- Proposal tx: [`0x9ca27bfb…1d06`](https://sepolia.etherscan.io/tx/0x9ca27bfbf88d685ac0dcc6d2f5d48c73d4bde665352a66cae5902b30ff861d06)
  block **12169177**, 2026-11-19T15:07:36Z, proposer `0x137F79Cc…0Df`, gas 821,063.
- `getResolution(2)`: proposed=true, proposal=**NO (1)**, evidence hash
  `0x90a8d312ebbb904afa2f76cd2f0f8f0da69c6cb86b44e6325bcd34338f496f22` (SHA-256 of the
  egamersworld match page snapshot showing the 2–0 result), evidence URI
  `https://egamersworld.com/valorant/match/fyQReleD60/keepbest-gaming-vs-a-team-ZD59-Lj4XM`.
- Market auto-closed on proposal (OPEN-past-deadline → CLOSED); state now **PROPOSED**.
- **Challenge window closes 2026-11-20T15:07:36Z** (24 h).

### PUB-06b — Bonded challenge (confirmed)

- Allowance approval: [`0x7b4a9653…d04`](https://sepolia.etherscan.io/tx/0x7b4a9653b89a13345a6fa21b42fb1914a9930f0222112243a0b78383de08bd04)
  block 12169198 (exact 10 ACON bond approval; the pre-approve challenge simulation correctly
  reverted `InsufficientTokenAllowance` — negative evidence recorded in the session).
- Challenge tx: [`0x7c0ddbe4…743`](https://sepolia.etherscan.io/tx/0x7c0ddbe44de2174b6952b63b4e115ceccac9c1dcc66fb66bd6ae3afd0df6b743)
  block **12169199**, 2026-11-19T15:12:12Z, challenger R01 `0x6a51…ffaCc`, gas 517,146.
- On-chain: challenger recorded, **bondEscrow = 10 ACON**, `totalChallengeBonds = 10`,
  market collateral unchanged (54.876…440), state **DISPUTED (3)**.

### PUB-07 — Real VRF request/callback and five-member committee

#### PUB-07a — Real VRF request (confirmed — the first serviced request in the project's history)

- Request tx: [`0x095e5358…4e35`](https://sepolia.etherscan.io/tx/0x095e53589a5cd579fc4d9b67f9afb7fda78e506853465aafa3a56b3be3374e35)
  block **12169201**, 2026-11-19T15:12:48Z, caller R01 (permissionless), gas 2,223,476,
  emitted `ResolverSelectionRequested` plus a coordinator-side acceptance event in the same
  receipt.
- **Chainlink VRF v2.5 request ID: `64454812201355125149715950417696302771148563436230064546743731846367863751153`**
- On-chain round state: `currentRequestId` matches the event; `snapshotFrozen = true` with
  **8 candidates** (R03–R10 — the eligible pool after R01/R02 exclusion); `hasRequest = true`,
  `fulfilled = false`; selection deadline **2026-11-26T15:12:48Z** (exactly seven days after
  the request).
- Subscription escrow at request time: **390.20 LINK**, `reqCount` 0 (no deductions at request
  time; the gate — ~260 LINK at the then-current feed with the immutable 2,000,000 callback
  gas — was satisfied for the first time, unlike the two underfunded M4-era requests and the
  11/17 diagnostics).

#### PUB-07b — Coordinator callback and five-member committee (confirmed)

The Chainlink coordinator fulfilled the request **60 seconds after it was requested** — the
first real VRF fulfillment in the project's history, closing the gap that left every M4-era
request unserviced (the funding gate documented in the 11/17–11/18 diagnostics and fixed by
the reviewed reserve in PR #58).

- Callback tx: [`0x90e45813…5d22`](https://sepolia.etherscan.io/tx/0x90e45813aefe950558afa346389a3dbe7267e959dbdec045a0155ed23bc75d22)
  block **12169206**, 2026-11-19T15:13:48Z (`ResolverCommitteeSelected`).
- Round state: `fulfilled = true`; committee selected by VRF randomness:
  **R05 `0xffa3…4dce`, R09 `0x748b…0a56`, R04 `0x2897…1b55`, R08 `0x7939…d755`,
  R03 `0xbedc…99f8`** — five distinct eligible addresses from the frozen eight-candidate pool.
- **Vote deadline: 2026-11-21T15:13:48Z** (48 hours after fulfillment); voteCounts (0, 0, 0).
- Subscription escrow after fulfillment: **390.189642 LINK** (fulfillment debit recorded by
  the coordinator; final charge accounting reconciled in PUB-10 with Matthew).

## PUB-08 — Three matching votes and settlement (confirmed)

The team scripted a **divided committee (three YES, two NO)** to demonstrate the
quorum-settlement mechanics; the settled outcome is the true result (YES — KeepBest Gaming
won 2–0). Vote order interleaved so all five committee votes were recorded before the third
matching YES triggered settlement.

| Order | Voter | Vote | Tx | Block |
|---|---|---|---|---|
| 1 | R04 `0x2897…1b55` | YES | [`0x2a342ac0…dc07`](https://sepolia.etherscan.io/tx/0x2a342ac0b55678d5bbf03638b4db1ba20015ec06904035a4f8876a19611adc07) | 12169235 |
| 2 | R05 `0xffa3…4dce` | YES | [`0x0456e179…fc99`](https://sepolia.etherscan.io/tx/0x0456e179063a313347c0b7550e3cd91f9737fbf0c88f18d28dddc6c806edfc99) | 12169236 |
| 3 | R03 `0xbedc…99f8` | NO | [`0x5bae24a9…1def`](https://sepolia.etherscan.io/tx/0x5bae24a960a1102e4bf51abbd2b4b8410dc2328d4479518070e69dd527091def) | 12169237 |
| 4 | R09 `0x748b…0a56` | NO | [`0x4f69e3a9…b12`](https://sepolia.etherscan.io/tx/0x4f69e3a952493a01873d12731df2d6a9d9b863f133238feabd5588274c0f7b12) | 12169245 |
| 5 | R08 `0x7939…d755` | **YES (3rd match — settles)** | [`0x4da4c265…f701`](https://sepolia.etherscan.io/tx/0x4da4c26583dfa90a57aec8a347beb70c4de24db7762a592ef2fc1192bfd3f701) | 12169246 |

(Broadcast order R04 → R05 → R03 → R09 → R08; an initial key-roster mislabel briefly pointed
R08's vote at R07's address and was corrected before broadcasting — R07 received a
`ResolverNotSelected` revert and no transaction.) Final on-chain record:

- `voteCounts (YES, NO, VOID) = (3, 2, 0)`; market **FINALIZED (6)** at block 12169246,
  2026-11-19T15:21:48Z.
- **`finalOutcome = YES`** — the committee overturned the deliberately incorrect NO proposal
  and settled the true result.
- **Bond resolved per the changed-outcome rule**: `bondEscrow = 0`,
  `totalChallengeBonds = 0`, and R01's ACON balance returned to its exact pre-challenge value
  (992.774453072819982559) — the 10 ACON bond refunded to the challenger. Market collateral was
  unchanged by settlement (54.876405572741439440 ACON).

## PUB-09 — Payouts and duplicate-claim rejection (confirmed)

Claims executed from the winning holders and the losing holder; every claim used the
`claimPayout(uint256)` path (the team's initial `claim(uint256)` calls reverted on selector
mismatch — corrected before broadcasting).

| Claim | Holder | Position | Payout | Tx | Block | UTC time (2026-11-19) |
|---|---|---|---|---|---|---|
| Winning | `0xB5ce…9A6A` | 17 YES | **17 ACON** | [`0xda3f38f4…004a`](https://sepolia.etherscan.io/tx/0xda3f38f438f5053bdccf2da5b9e659f9efc485cfdbbf1a02061b5611525004a4) | 12169251 | 15:22:48Z |
| Winning | R01 `0x6a51…ffaCc` | 11 YES | **11 ACON** | [`0x256772e1…e92`](https://sepolia.etherscan.io/tx/0x256772e1aa887d1e4f2060574161b4b54480ccf415980c64395609ebf0108e92) | 12169252 | 15:23:00Z |
| Losing close-out | R02 `0xcddb…15A8C` | 11 NO | **0 ACON** (closes the position) | [`0x85f33a8c…cf24`](https://sepolia.etherscan.io/tx/0x85f33a8c5ebc00cbbf8a1ee45c30a704831b8d34a5f5bbaf51cddd680961cf24) | 12169254 | 15:23:24Z |

- Wallet reconciliation exact (wei): Benny post-claim `960.407877055525024275` (+17 over
  pre-claim `943.407877055525024275`); R01 post-claim `1003.774453072819982559` (+11 over
  post-refund `992.774453072819982559`).
- **Duplicate-claim rejection**: a read-only `claimPayout(2)` from Benny's address reverts
  `AlreadyClaimed` (`hasClaimed = true` for all three wallets).

## PUB-10 — Bond, liability and creator-surplus reconciliation (confirmed)

- **Challenge bond** (changed-outcome rule): the committee overturned the NO proposal, so the
  10 ACON bond **refunded to the challenger** R01 at settlement — balance verified back to its
  exact pre-challenge value; `bondEscrow = 0`, `totalChallengeBonds = 0`, market collateral
  unchanged through settlement.
- **Creator surplus**: `withdrawableSurplus(2)` = `26.876405572741439440` = collateral
  54.876405572741439440 − 28 ACON winning liability; withdrawn by the creator
  [`0x94460bde…a3a`](https://sepolia.etherscan.io/tx/0x94460bdec7b3d6416a21397ee6b6c92845e2621b70c4aafe1f680ff762da0a3a)
  block 12169256, **2026-11-19T15:23:48Z** (`CreatorSurplusWithdrawn`). Benny's final ACON `987.284282628266463715` =
  post-claim `960.407877055525024275` + surplus `26.876405572741439440` — exact.
- **Terminal accounting**: market 2 collateral **0**; total liabilities 28 ACON paid to YES
  holders; losing close-out paid 0 (R02 final ACON `996.22554692718001744`). The contract's
  global residual balance (50.87640557274144) belongs to market 1 (FlyQuest, still live: 7 YES
  / 24 NO outstanding + its 34.657… subsidy) — verified separately, not part of this journey.

## Cross-layer reflection status (pending operator indexer window)

The operator indexer stopped at safe block 12167172 (last update 2026-11-19T08:09:31Z), which
covers the trades (PUB-04/05 rows carry verified DB/API reflection) but predates the proposal,
challenge, VRF, votes, settlement, claims and surplus (blocks 12169177–12169256). The public
API therefore still reports market 2 as OPEN with final outcome unset, and the DB/API/UI cells
of PUB-06–10 are **pending** until the operator resumes the indexer and the catch-up is
verified. The on-chain columns above stand on their own: every hash, block and amount was read
directly from Sepolia. Issue #56 stays open until that cross-layer verification is recorded.

## On-chain journey complete

The on-chain leg of every issue #56 acceptance criterion is evidenced live on Sepolia: guarded
sell (PUB-05 + the M4-era quote-equals-proceeds record), reviewed proposal and bonded challenge
(PUB-06), real VRF request ID/callback and five-member committee (PUB-07), three matching votes
and truthful settlement (PUB-08), payouts and duplicate-claim rejection (PUB-09), and full
bond/liability/surplus reconciliation (PUB-10). Local Anvil evidence (LOC-05/06/07) remains
separately labeled and does not substitute for this record. The DB/API/UI verification of the
post-trading rows completes the issue's cross-layer criterion once the indexer resumes.

## Funding record

- Subscription escrow: 10 LINK (2026-11-02) → 50 → 90.2 → 165.2 → 190.2 → 215.2 → 265.2
  → **290.20 LINK** (2026-11-19, recorded before the dispute path). Fulfillment charges deduct
  at callback; the request-time gate requires the reviewed reserve (~260 at the 11/19 feed).
- No wallet holds LINK; the escrow is the only LINK balance the journey spends.
