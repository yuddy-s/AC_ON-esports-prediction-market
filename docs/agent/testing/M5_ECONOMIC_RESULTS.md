# Milestone 5 Economic Testing and Accounting Results

Owner: Matthew Leong. Local rerun completed November 18 2026 at 00:14 EST. Public receipt observations were recorded on November 17 2026 ET. Shared Supabase, local UI and retrospective public-trade checks completed that afternoon; final database/API recheck passed at 16:01 EST.

The local contract regression suite passed **120 tests with zero failures and zero skips**. Public Sepolia observations reconcile the market 0 VOID payout, challenge-bond refund and creator-surplus withdrawal exactly. After Supabase resumed, the corrected local indexer caught up the shared database; database rows, local API responses and local UI now agree with those receipts. The five existing public buys and one sell also reconcile exactly. **Hosted Render API/Vercel frontend acceptance remains pending because their URLs have not been identified.** Issue #56 remains incomplete because a successful real-market VRF callback, committee and resolver voting have not been demonstrated.

## Section 1 Integration Test Results

The ECON labels identify this economics supplement; canonical PUB IDs are retained in Scenario. Pass chain applies only to the named receipt/accounting subcheck.

| Test ID | Scenario | Expected result | Actual result | Pass or Fail |
|---|---|---|---|---|
| ECON-01 | Local contract economic regressions | Pricing and accounting assertions hold under the full repository profile. | 120 tests passed. Fuzz: 256 runs. Invariants: 256 x 500. All 72 trade vectors and 85 correction bounds agree. | Pass local |
| ECON-02 | PUB-09 VOID payout and duplicate claim | Pay 125.0055 ACON; clear positions; reject a repeat claim. | Exact payout received; liability and both positions became zero. Repeat eth_call: AlreadyClaimed. | Pass chain |
| ECON-03 | PUB-10 challenge bond refund | Refund 10 ACON without reducing market collateral. | 10 ACON refunded; escrow became zero; market collateral was unchanged. | Pass chain |
| ECON-04 | PUB-10 creator surplus | Withdraw collateral above remaining liability. | 40.665164062370061911 ACON withdrawn; collateral and liability became zero. Repeat eth_call: NoSurplus. | Pass chain |
| ECON-05 | PUB-09 and PUB-10 cross layer agreement | Shared database, API and hosted UI match receipts. | Shared Supabase caught up with corrected handler; exact receipts, quantities and claim block match through local API/UI. Repeated synchronization processed no duplicate events. Hosted Render/Vercel verification remains pending. | Partial; hosted pending |
| ECON-06 | PUB-04 and PUB-05 public buy/sell reconciliation | Quotes, transfers, position and collateral changes agree with indexed history. | Five existing buys and one sell match historical quotes, slippage guards, canonical receipts, exact ACON transfers, wallet/contract balance changes, positions, collateral and shared-database API history. Local UI shows all six receipts; tiny values are rounded for display. | Pass accounting; hosted pending |

Public actions used Ethereum Sepolia chain ID 11155111 and PredictionMarket `0x03ae48f03C7822540a91DA2168602bd49dC510E9`, with ACON `0xf85b2278a810410c6AE0b7490d34671E0C8e6E90`. This is the expired resolver-selection VOID path; it does not evidence successful VRF committee selection or voting. The local frontend was verified against the restored shared database and local API; hosted public-stack UI/API verification remains outstanding. Duplicate claim and repeated surplus checks were read-only `eth_call` simulations against recorded post-transaction blocks; no second transactions were broadcast.

### Local rerun evidence

- Working tree: `dev` at `8f772eb9e1b633db5b4688450388c24647e8ec36`, including the local deployment-preflight and indexer fixes recorded in [run metadata](../../../deployments/m5-economics-2026-11-18/run-metadata.json). This is a local working-tree result, not a CI result.
- Compiler: Solidity 0.8.24, optimizer 200, via IR, Cancun. The nine production Solidity source files match the recorded November 2 deployed source snapshot; [source comparison](../../../deployments/m5-economics-2026-11-18/configuration-and-source-check.json) does not claim a fresh runtime/deployment verification.
- Full suite: 120 passed, 0 failed, 0 skipped across 12 test suites. See [gzip-compressed raw Foundry JSON](../../../deployments/m5-economics-2026-11-18/contract-tests.json.gz) and [parsed summary](../../../deployments/m5-economics-2026-11-18/contract-test-summary.json). Decompress with `gzip -dc deployments/m5-economics-2026-11-18/contract-tests.json.gz` from the repository root.
- Fuzz runs: 256 per fuzz test. Invariant settings: 256 runs, depth 500, fail on handler revert enabled. Handler calls can include guarded no-ops and caught invalid quotes; calls are not all successful trades.
- Seed: `0x0000000000000000000000000000000000000000000000000000000000000005`.
- Independent pricing check: 72 mathematical trade vectors and 85 correction bounds agree at 160 and 220 decimal digits. [Check output](../../../deployments/m5-economics-2026-11-18/pricing-reference-check.json).
- Indexer payout regression: 3 tests passed on local SQLite. This reruns the projection fix locally; it does not exercise Supabase or a deployed API. [Backend check](../../../deployments/m5-economics-2026-11-18/indexer-regression-check.json).
- `forge fmt --check` passed. [ABI and runtime handoff check](../../../deployments/m5-economics-2026-11-18/handoff-check.json) records the exact result; this local check does not claim a fresh Sepolia deployment.

| Suite | Passed tests | Stateful or fuzz coverage |
|---|---:|---|
| `test/ACONTestToken.t.sol:ACONTestTokenTest` | 4 | Deterministic regressions |
| `test/Deployment.t.sol:DeploymentTest` | 6 | Deterministic regressions |
| `test/LMSR.t.sol:LMSRInvariantTest` | 1 | invariantMarketMakerLossIsBoundedBySubsidy: 256 runs, 128000 calls, 0 reverts |
| `test/LMSR.t.sol:LMSRTest` | 20 | 3 fuzz tests |
| `test/MarketEconomics.t.sol:MarketPricingSemanticsTest` | 1 | Deterministic regressions |
| `test/MarketEconomics.t.sol:MarketSettlementInvariantTest` | 1 | invariantClaimsBondsAndSurplusPreserveLiabilities: 256 runs, 128000 calls, 0 reverts |
| `test/MarketEconomics.t.sol:MarketTradingInvariantTest` | 1 | invariantRepeatedBuysAndSellsPreserveEconomics: 256 runs, 128000 calls, 0 reverts |
| `test/MarketLifecycle.t.sol:MarketLifecycleTest` | 20 | Deterministic regressions |
| `test/MarketPricing.t.sol:MarketPricingTest` | 9 | 2 fuzz tests |
| `test/MarketSecurity.t.sol:MarketSecurityTest` | 18 | 1 fuzz test |
| `test/PredictionMarket.t.sol:PredictionMarketTest` | 16 | Deterministic regressions |
| `test/Resolvers.t.sol:ResolverTest` | 23 | 1 fuzz test |

The three invariant campaigns generated 384,000 handler calls in total, with zero handler reverts. This includes guarded no-ops and caught invalid quotes, so it is not a count of successful trades. The historical buy-only LMSR harness and the current multi-market economic handlers are identified separately in the raw results.

Reproduce from `contracts/`:

The recorded run included both fixes before they were split into PRs #57 and #58. Reproduce the complete 120-test result with both fixes present; the evidence-only branch does not itself include #58's deployment-preflight changes. The recorded source hashes identify that historical working tree.

```bash
FOUNDRY_FUZZ_RUNS=256 FOUNDRY_INVARIANT_RUNS=256 FOUNDRY_INVARIANT_DEPTH=500 FOUNDRY_INVARIANT_FAIL_ON_REVERT=true forge test --offline --json --fuzz-seed 0x0000000000000000000000000000000000000000000000000000000000000005
python3 script/pricing_reference.py --check
forge fmt --check
python3 script/export_handoff.py --check
```

### Public accounting reconciliation

All values below are ACON tokens; one token has 18 decimal places. Before terminal settlement, the displayed liability is the prospective VOID reserve computed from recorded outstanding shares. Challenge escrow is separate from market collateral.

| Recorded stage | Market collateral | VOID liability | Bond escrow | Contract ACON balance |
|---|---:|---:|---:|---:|
| Before VOID settlement | 165.670664062370061911 | 125.0055 | 10 | 175.670664062370061911 |
| After VOID settlement | 165.670664062370061911 | 125.0055 | 0 | 165.670664062370061911 |
| After payout | 40.665164062370061911 | 0 | 0 | 40.665164062370061911 |
| After creator surplus withdrawal | 0 | 0 | 0 | 0 |

Recorded positions before the claim were **150.01 YES** and **100.001 NO**. The combined VOID claim was `(150.01 + 100.001) / 2 = 125.0055 ACON`. The general contract rule floors the combined per-wallet payout and ceilings the remaining reserve in base units; this particular combined amount divides exactly.

```text
165.670664062370061911 = 125.0055 + 40.665164062370061911
Market collateral       VOID payout  Creator surplus

175.670664062370061911 = 10 + 125.0055 + 40.665164062370061911
Initial contract balance  Bond refund  Payout  Surplus
```

The creator/trader wallet rose from 834.329335937629938089 to 959.334835937629938089 ACON after the claim and to exactly 1000 ACON after the surplus withdrawal. The challenger separately recovered the 10 ACON bond. At the last recorded surplus snapshot, global collateral, challenge bonds, contract ACON balance, market quantities, positions, claimable amount and remaining liability were zero. Sepolia ETH gas fees are separate from this ACON accounting.

| Action | Block | Public receipt |
|---|---:|---|
| VOID settlement and bond refund | 12158923 | [0x569d65ff15925d37ff0dabd00a8033e708a923fa68de8dd1e0cceef6cbcb4dcb](https://sepolia.etherscan.io/tx/0x569d65ff15925d37ff0dabd00a8033e708a923fa68de8dd1e0cceef6cbcb4dcb) |
| VOID payout | 12158940 | [0xc7d625cf7ddb708977c3c1e44cb6f4d23a650915a041d9ac393754cb8e5fa5f9](https://sepolia.etherscan.io/tx/0xc7d625cf7ddb708977c3c1e44cb6f4d23a650915a041d9ac393754cb8e5fa5f9) |
| Creator surplus withdrawal | 12158955 | [0xe4f7b7e1c8e241007fa0bf435ccd5e48e303af4c67dba2abd5f084312b1eae13](https://sepolia.etherscan.io/tx/0xe4f7b7e1c8e241007fa0bf435ccd5e48e303af4c67dba2abd5f084312b1eae13) |

The [offline reconciliation](../../../deployments/m5-economics-2026-11-18/accounting-reconciliation.json) checks arithmetic and consistency across the saved receipt observations. Reproduce with `python3 deployments/m5-economics-2026-11-18/reconcile-accounting.py` from the repository root. It performs no RPC calls and does not replace the original receipt verification.

Receipt sources: [VOID settlement](../../../deployments/sepolia-2026-11-02/market-0-void-settlement-evidence.json), [payout](../../../deployments/sepolia-2026-11-02/market-0-void-payout-evidence.json), [creator surplus](../../../deployments/sepolia-2026-11-02/market-0-creator-surplus-evidence.json).

### Restored shared database and integration verification

Supabase accepted the existing connection after the owner resumed the project. Migration revision was `20261102_0008`. Its checkpoint had stopped at safe block 12054434 on November 3, before settlement. A deployment-scoped snapshot was retained privately before any writes. The corrected handler from PR #57, commit `81850e9146e0512cc2d62cbbac05d90a6de2a5ee`, applied nine missing confirmed events through safe block 12163724. No projection deletion or full rebuild was necessary because the claim had not been indexed previously. Canonical block anchors were checked against the configured RPC, and complete historical logs were obtained from an archive endpoint. The catch-up committed only after accounting assertions passed.

Shared rows now show market 0 VOID, final outcome 2, both market quantities and wallet positions zero, `claimed=true`, payout `125005500000000000000` base units and position update block 12158940. Event records preserve the exact 10 ACON bond refund and 40.665164062370061911 ACON surplus withdrawal. A subsequent live synchronization and immediate repeat processed zero duplicate events. The recorded local API status was two blocks behind the observed head, matching the configured confirmation depth.

All seven checked GET endpoints returned HTTP 200: health, indexer status, market, resolution, claims, history and portfolio. The local market UI showed VOID, already claimed, zero outstanding shares and collateral, six indexed trades and a 1000 ACON wallet balance. The portfolio showed one claimed market, zero YES/NO shares, no ready payout and zero available creator surplus. UI formatting rounds very small historical values; exact comparisons use raw API base units and receipts.

A later local service recheck encountered a timeout and the polling worker exited following RPC/DNS failures. Supabase still passed a separate read-only connection check. After restarting the local API and running two fresh indexer syncs, all seven API checks passed again at 16:01 EST with safe block 12163950, two below the observed head. This verifies recovery and accounting consistency; it is not an uptime or continuously hosted worker test. The local indexer was used for verification and is not a replacement for a deployed polling service.

Evidence: [shared catch-up](../../../deployments/m5-economics-2026-11-18/supabase-catchup-verification.json), [API responses and assertions](../../../deployments/m5-economics-2026-11-18/supabase-local-api-verification.json), [repeat synchronization](../../../deployments/m5-economics-2026-11-18/live-indexer-idempotence.json), [current chain state](../../../deployments/m5-economics-2026-11-18/market-0-chain-recheck.json), and [local market screenshot](../../../deployments/m5-economics-2026-11-18/supabase-market-0-ui.png). This verifies a local backend/frontend against the real shared Supabase database; it does not establish that a hosted worker or API is running the corrected code.

### Existing public buy and sell reconciliation

The six transactions were originally mined November 2 ET; this is a retrospective M5 reconciliation, with no new trades submitted. Historical quotes at the preceding block equal executed amounts. Each transaction also passes slippage, token transfer, wallet/contract balance, collateral, position/quantity and canonical receipt checks; shared-database API history matches the raw receipt values.

| Action | Shares | Quote and payment/proceeds (ACON) | Block |
|---|---:|---:|---:|
| Buy YES | 0.02 | 0.010000999999993334 | 12052315 |
| Buy NO | 0.001 | 0.000499902500001237 | 12052387 |
| Buy NO | 100 | 71.681805856233194196 | 12052394 |
| Sell YES | 0.01 | 0.001192323234939916 | 12052699 |
| Buy YES | 100 | 28.314385767001750878 | 12052758 |
| Buy YES | 50 | 31.007804831872796711 | 12052761 |

Creator subsidy 34.657359027997265471 plus net trade payments 131.013305034372796440 equals the pre-settlement collateral 165.670664062370061911 ACON. [Per-transaction checks, hashes and timestamps](../../../deployments/m5-economics-2026-11-18/public-trade-reconciliation.json).

## Section 2 Bugs Found and Fixes

| Bug ID | Description | Severity | Fix and status |
|---|---|---|---|
| ECON-B1 | PayoutClaimed cleared wallet positions but left indexed market YES/NO quantities and the position updated block stale. | P2 degraded indexed accounting | PR #57 subtracts claimed YES/NO shares and updates the position block. Three focused tests and the earlier full 130-test backend rerun passed. On November 18, the corrected local worker caught up shared Supabase and verified zero quantities, exact payout and correct claim block through local API/UI. Status: shared database verified; merge and hosted rollout verification pending. |
| ECON-B2 | Deployment and authority verification treated any positive LINK balance as funded, allowing a balance below the reviewed VRF reserve to pass. | P1 major journey risk | Local scripts require a positive reviewed VRF_MINIMUM_LINK_BALANCE_WEI threshold and reject lower balances. Six deployment tests pass within the new full contract rerun. The operator must review the current billing estimate and concurrency buffer; the script does not calculate the reserve or prove VRF liveness. Status: fixed and regression tested locally; not merged or deployed. |

The pre-M5 mathematical pricing correction is a retained regression, not a newly discovered M5 defect. The current M5 run rechecks the prior reported sell floor 4,750,415,558,917,673,486 base units and reverse-buy ceiling 4,750,415,558,917,673,487, leaving one base unit in collateral.

## Parameters and Limitations

| Parameter or rule | Value and rationale |
|---|---|
| Token units | 18 decimals; calculations and receipt comparisons use integer base units. |
| LMSR liquidity parameter | b = 50 ACON; controls price sensitivity and the b ln 2 worst-case loss bound. |
| Creator subsidy | 34.657359027997265471 ACON, the integer ceiling of b ln 2 in token base units. |
| Input domain | At most 100 shares per trade and 2000 outstanding shares per outcome; the numerical implementation is tested within this bounded domain. |
| Directed rounding | Successful buys use the mathematical ceiling; sells use the floor. Uncertifiable intervals revert. A positive sell with zero floored return reverts TradeTooSmall. |
| Challenge bond | 10 ACON held separately; refunded when the final outcome changes the proposal, otherwise added to that market collateral. |
| Claims and surplus | Winning shares pay one-for-one. VOID combines both holdings and floors per wallet, while the outstanding reserve is ceiled. Creator surplus is terminal collateral above remaining liability. |

Local fuzzing and invariants sample reachable states and do not prove every possible input. Local resolver tests use a coordinator mock and cannot establish real Chainlink liveness. Token-ledger equalities cover the intended ACON flows; unsolicited token donations and fee-on-transfer or rebasing token behavior are outside this test evidence.

Public evidence covers the single-wallet VOID path on market 0 and retrospective reconciliation of its five buys and one sell. YES/NO settlement, multiple-wallet claim ordering, bond forfeiture and market isolation are covered locally; their public-stack acceptance is not claimed. No new public trades were submitted for this verification.

PUB-04/PUB-05 accounting reconciliation and PUB-09/PUB-10 shared database plus local API/UI checks now pass. Hosted Render/Vercel acceptance and issue #56 real VRF/committee/voting remain open. The [16:11–16:13 EST VRF recheck](../../../deployments/sepolia-2026-11-17-vrf-diagnostic/RECHECK-2026-11-18.md) records zero fulfillments, unchanged balances and an estimated funding gap; it does not establish successful fulfillment. User-guide and developer-guide completion are separate team deliverables.

The two fixes were committed and pushed as [PR #57](https://github.com/yuddy-s/AC_ON-esports-prediction-market/pull/57) and [PR #58](https://github.com/yuddy-s/AC_ON-esports-prediction-market/pull/58). This report and its linked verification records form the documentation/evidence follow-up. The confirmed-event catch-up wrote the shared database's derived projections; no wallet action or new Sepolia transaction was made for this verification.
