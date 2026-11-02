# Contract verification record

Status: **mathematical floor-sell / ceiling-buy correction and stacked economic proof locally tested
on 2026-11-01; numerical/ABI/economic review and fresh deployment pending**.
Source/dependency/ABI/runtime-template digests are in
[`deployments/build.json`](../../../deployments/build.json).
This record covers Benny's contract slice. The [M4 milestone test plan](../milestones/MILESTONE_4.md#full-documented-test-plan)
also requires frontend, backend, oracle/indexer and cross-layer evidence from their owners.

## Results

| Check | Local result |
|---|---|
| Solidity formatting | `forge fmt --check` passed |
| Production compilation | Solc 0.8.24, optimizer 200, `via_ir=true`; the current `script/Deploy.s.sol` compiles |
| Full Foundry suite | **119 passed, 0 failed, 0 skipped** across twelve suites |
| Lifecycle tests | 20 lifecycle, 23 resolver, 18 security/accounting, 5 deployment-helper tests |
| Token/trading/math tests | 16 real-token market integration, 9 mathematical-pricing tests, 4 ACON, 20 historical LMSR deterministic/fuzz, 1 rounding regression, 3 grouped invariant suites |
| Independent pricing references | 72 mathematical trade vectors checked for both outcomes/directions, 85 correction bounds; generated reference results agree at 160/220 decimal digits |
| Fuzz/invariant runs | 256 runs per fuzz test; historical LMSR plus M4 trading and settlement invariants each run 256 × 500 calls = **384,000 total state-machine calls**, zero reverts |
| Local Anvil | **Six journeys, 104 successful transactions**, including a captured failed VRF request and recovery; real ACON/pricing/registry/market, explicit mock coordinator |
| ABI/event handoff | Four exact JSON ABI exports, source/dependency/runtime-template hashes, generated reference and required event examples validate |
| Static analysis | Slither 0.11.3: **0 high, 7 medium, 14 low**; `--fail-high` passes with findings retained below |

The separate deployment-helper tests execute all 15 Safe setup CALL payloads against a Safe
execution mock and a subscription mock. They verify both admin handoffs, former-admin removal,
distinct narrow roles, consumer registration and ten resolver addresses; reject a pending handoff,
duplicate/conflicted/undersized pools and mismatched pending admins. They do not validate real
Safe signatures or a live subscription. Review caught and fixed a setup-plan/verifier mismatch:
the plan now rejects assigning an operational role to the Safe, and verification rejects a
resolver pool containing the Safe, registrar or proposer.

### Production runtime sizes

| Contract | Bytes | EIP-170 limit |
|---|---:|---:|
| PredictionMarket | 23,929 | 24,576 |
| MarketPricing | 3,185 | 24,576 |
| ResolverRegistry | 2,524 | 24,576 |
| ACONTestToken | 1,716 | 24,576 |

Market headroom is **647 bytes**. CI checks these production contracts independently of script/test
harnesses. `forge build --sizes` over every script also flags the large local deployment harness
because it embeds creation bytecode; that harness is executed by Forge, not deployed as a production
contract. Use the production test/export check for the actual deployment size gate.

## Reproduce

Use Foundry **v1.8.3**, Python 3.11+, and the pinned PRBMath submodule. From `contracts/`:

```bash
export PATH="$HOME/.foundry/bin:$PATH"
export FOUNDRY_OUT=out/current FOUNDRY_CACHE_PATH=cache/current
forge fmt --check
forge build
forge build script/Deploy.s.sol
forge test --summary
python3 script/export_handoff.py --check
python3 script/pricing_reference.py --check
python3 script/smoke.py --start-anvil
```

The smoke runner owns a disposable node on unused localhost port 18545 and stops it on success
or failure. It rejects occupied ports, nonlocal RPC targets, non-31337 chain IDs and a used admin
nonce. `--rpc-url http://127.0.0.1:<unused-port>` changes the port. All fixtures are explicitly
fictional; timeout advances use Anvil RPC time control. It requires no private keys or hosted services.

For a deliberate handoff update, run the smoke first, then `python3 script/export_handoff.py`
and `--check`. Exported logs are actual receipts, not constructed examples. Raw full evidence is
`contracts/cache/verification/anvil-smoke.json`; the concise summary and representative events are public
draft artifacts. Two extra blocks are mined and all receipt blocks are checked against head minus two.

### Six transaction journeys

1. Fund/create, buy both sides, sell with exact proceeds, early close, propose YES, wait 24 hours,
   finalize, claim winning shares, withdraw remaining creator surplus.
2. Challenge NO, force the mock coordinator's first request to fail and capture the market's
   `ResolverSelectionRequestFailed` log, recover after 30 minutes, retry again and ignore the
   superseded callback, install the current committee, three YES votes, refund the changed-outcome
   bond, claim. Both retries retain the original frozen candidate pool and selection deadline.
3. Propose VOID, wait the same challenge period, combine YES and NO holdings into one payout.
4. Seven days without a proposal, permissionless resolver selection, quorum and claim.
5. No first-round quorum, replacement committee, second voting deadline, VOID and claim.
6. Insufficient resolver pool, fixed seven-day formation deadline, VOID and claim.

Final market collateral, challenge escrow and the contract's ACON balance all reconcile to zero
after these journeys' claims/surplus withdrawals. This is a contract-level transaction test, not
frontend/backend integration or proof of real Chainlink/Safe behavior.

### Failed-request event handoff

`deployments/event-fixtures.anvil.json` includes a real Anvil receipt log for
`ResolverSelectionRequestFailed(uint256,uint8,bytes32,uint256)`. The coordinator reverts with
the mock's `RequestFailed()` error; the market catches it, so the outer transaction succeeds
and its failure event persists. The smoke checks:

- the emitter, signature topic, indexed market ID and round;
- `reasonHash = keccak256` of the actual mock error's ABI encoding;
- `retryAfter = failure block timestamp + 1800` and the fixed seven-day selection deadline;
- a frozen candidate pool with no active request after failure, followed by successful recovery.

The exporter now requires this event during both generation and `--check`. The previous fixture
set was explicitly tested and rejected with `Missing required event examples:
ResolverSelectionRequestFailed`; the regenerated set passes. Its ABI SHA-256 is computed from
the compiled `PredictionMarket.abi.json` and checked against `build.json`, alongside topic/data
decoding. The focused Foundry tests `testRequestFailureKeepsSnapshotAndCanRetryAtThirtyMinutes`
and `testRetryFailureAlsoInvalidatesOlderOutstandingRequest` also passed for this handoff update.

## Security and correctness coverage

| Area | Exercised behavior |
|---|---|
| Fixtures | Registrar permission; exact key/team order; immutable funded metadata; revision-race rejection; one market; failed funding rollback; deadline margin; historical registrar conflicts |
| Trades | YES/NO positions and exact token changes; bounded sizes/quantities; actual intervening-trade buy/sell slippage; no trade at/after deadline; no unowned sells; tiny sell rejection |
| Mathematical pricing | Reported 464-unit discrepancy; direct high-precision references; directed interval enclosure; exact reflected states; near-integer fuzzing; no inverse-trade gain; 16 repeated real-token round trips; uncertifiable intervals revert |
| Lifecycle | Immutable authorized proposal; 24-hour edge; no self/duplicate challenge; separate bond; late proposal cannot race no-proposal expiry; unchallenged finalize |
| Resolver | All conflicts; distinct frozen candidates; shortages/replenishment; retries/failures; request ID zero; cross-market identity; unauthorized/stale/duplicate/malformed/late callbacks; preserved snapshot/deadline |
| Voting | Selected-only, once per round, strict 48-hour edge; YES/NO/VOID quorum; fresh replacement and reuse fallback; formation expiry and second-round VOID |
| Funds | Winning/VOID claims; combined odd-unit rounding and ceiling reserves; losing zero claim; duplicate/no-position rejection; creator-only reserved surplus; market isolation |
| Adversarial interactions | False-returning and fee-like transfers; rollback of token/position/claim/bond/vote effects; incoming/outgoing/coordinator reentry; invalid raw enum calldata |
| Administration | Two-step transfer removes former admin; no accidental default-admin renunciation/duplication; narrow-role recovery; no admin rewrite of a proposal or withdrawal of user claims |

The mixed-market fuzz test still supplies a compact end-to-end integration property. Matthew's
independent [M4 economic proof](M4_ECONOMIC_PROOF.md) now adds two invariant campaigns beyond it:

- 128,000 repeated YES/NO buy/sell calls across two markets and two wallets, continuously checking
  quote-to-collateral changes under ceiling-buy/floor-sell rounding, creator-subsidy preservation,
  position/quantity conservation, winning and VOID coverage, token conservation and market isolation;
- 128,000 claim/duplicate-claim/surplus/bond-settlement calls across YES, NO, VOID and challenged
  markets, continuously checking payout units, remaining liabilities, separate bond escrow and
  cross-market isolation.

Together with the retained 128,000-call M3 buy-only invariant, the suite executes 384,000 stateful
calls at the repository's standard 256 campaigns × 500 depth. The deterministic sell regression
locks the mathematical floor, reverse-buy ceiling, and one-base-unit residue for the reported vector.

The [rounding correction record](PRICING_ROUNDING.md) explains the new numerical enclosure and
the corresponding ceil-buy change. Matthew's revised
[economic proof](M4_ECONOMIC_PROOF.md) replaces the superseded exact rounded-potential equality
with the successful-trade ledger inequality and direct winning/VOID liability checks.

### Coverage measurement

The coverage step uses **32 invariant runs at depth 100**, scoped through environment variables
on that step alone. The normal `forge test` job retains the `foundry.toml` defaults of **256 runs
at depth 500**. Across the three invariant campaigns this reduces the instrumented rerun from
384,000 to **9,600 handler calls** (40 times fewer); it does not reduce the full economic test
campaign or the 256-run stateless fuzz tests. Failure-on-revert remains enabled.

Coverage still runs every suite and excludes only the production runtime-size assertion, because
minimum-IR instrumentation changes bytecode size. The normal test job and ABI exporter enforce
production size. All market tests exercise the same current `PredictionMarket`.

The reduced-budget local run passed **118 tests, 0 failed, 0 skipped** across twelve suites.
Each invariant campaign completed 3,200 handler calls with zero handler reverts. Compilation
took 37.40 seconds and test execution took 55.75 seconds (about 93 seconds combined, excluding
setup and static analysis). GitHub runner/setup costs will affect the hosted duration.

An LCOV comparison against the recorded pre-#38 full-budget report retained **every previously
covered production line, branch and function** across all seven source files, not just the same
aggregate percentages. The local comparison report is
`contracts/cache/verification/lcov-coverage-budget.info`; CI continues to upload `lcov.info`.

```bash
FOUNDRY_OUT=out/coverage FOUNDRY_CACHE_PATH=cache/coverage \
  FOUNDRY_INVARIANT_RUNS=32 FOUNDRY_INVARIANT_DEPTH=100 \
  forge coverage --ir-minimum --exclude-tests --no-match-coverage '^script/' \
  --no-match-test testProductionContractsFitEip170RuntimeLimit \
  --report summary --report lcov --report-file cache/verification/lcov.info
```

| Production file | Lines | Statements | Branches | Functions |
|---|---:|---:|---:|---:|
| MarketAccess | 97.44% (38/39) | 89.74% | 72.73% | 100% |
| LMSRBounds | 100% (64/64) | 100% | 100% | 100% |
| MarketPricing | 94.44% (17/18) | 96.30% | 100% | 100% |
| PredictionMarket | 98.47% (386/392) | 95.66% | 83.84% | 97.73% |
| ResolverRegistry | 90% (18/20) | 90.48% | 75% | 75% |
| All production source | 98.34% (591/601) | 95.86% | 83.21% | 97.47% |

This table records the reduced-budget results, which match the recorded full-budget baseline.
These are measured counts, not promised future thresholds. Minimum-IR source maps
can be imprecise and its bytecode differs from production; the normal test suite and exporter
still enforce production runtime size. Scripts/tests/dependencies are excluded from the table.
LCOV is retained under the ignored cache and uploaded in CI.

## Slither finding review

Install into a local virtual environment using `contracts/security-requirements.txt`, then run
from `contracts/` with its executable on PATH:

```bash
FOUNDRY_OUT=out/security FOUNDRY_CACHE_PATH=cache/security \
  slither . --filter-paths 'lib/|test/|script/' --fail-high \
  --json cache/verification/slither-rounding-final.json
```

Use an unused report filename when rerunning; Slither does not overwrite existing reports.
The current local report is `cache/verification/slither-rounding-final.json` (CI writes `slither.json`). Output/cache isolation keeps
Slither's `forge clean` away from normal and coverage artifacts. The scan covers all current
first-party production contracts; it excludes library, test and script findings.

| Finding | Count/severity | Review and evidence |
|---|---|---|
| `divide-before-multiply` | 2 medium | In `LMSRBounds`, `Q/(64*b)` is an exact integer because the constants divide exactly; multiplying by imbalance loses no precision. The log lower-bound term deliberately uses `2*floor(power/denominator)`, which is at most the true term. The upper bound encloses it separately and certification checks final rounding. Independent correction vectors test enclosure. |
| `unused-return` | 3 medium | Buy pricing uses the certified ceiling and both sell branches use the certified floor, intentionally ignoring the unused member of `LMSRBounds.trade`'s pair. This is not an ignored token-transfer success flag; certification executes before either amount is returned. |
| `incorrect-equality` | 1 medium | `_eligibleCandidates`: `round == 2` intentionally identifies the only replacement round. Round is assigned internally to 1/2, not a balance or an unpredictable timestamp. Replacement/exclusion/fallback tests exercise both branches. |
| `reentrancy-no-eth` | 1 medium | `_requestRandomness` records the coordinator-returned ID after the external request. All market lifecycle entry points and callbacks share the lock; snapshot, last-attempt time and prior-request invalidation precede the call. `testCoordinatorRequestCannotReenterSelection` checks the actual lock error and that no nested request installs. The immutable coordinator must be the reviewed Chainlink deployment. |
| `reentrancy-benign` | 1 low | Same coordinator-returned request-ID association after the guarded request. Incoming/outgoing market payment accounting precedes token interactions. The coordinator reentry test verifies that a nested lifecycle call cannot install a request. |
| `timestamp` | 13 low | Deliberate trading/challenge/selection/vote/retry deadlines, plus propagated taint into round-2 candidate filtering. Exact boundary and late-callback tests cover these transitions. Time is not used as committee randomness. |

CI fails on high-severity findings and retains the full report, including these findings.
No global detector suppression was added. This review is not an external security audit or
economic sign-off. Remaining integration concerns include real coordinator/callback gas behavior,
funded subscription liveness, Safe signatures/owner verification, and the actual resolver pool's
eligibility/gas budget. Registry scans/callback pool copying grow with the allowlist; the local
smoke uses ten addresses, not an unbounded-pool gas guarantee.

## CI and remaining acceptance

The existing contract build/test check now also validates the exact handoff and runs disposable
Anvil journeys. A separate analysis job runs pinned Slither and coverage and uploads their reports.
PR #37's original CI passed, and the rounding correction was published at `28fa936`. This
failed-request fixture update has been validated locally and still needs publication and hosted
CI. Final source/build digest pinning remains pending PR #38 reconciliation and team approval;
regenerate and recheck the handoff if that reconciliation changes the source or ABI.

Before M4 release: record Matthew's economics/payout approval and consumer ABI freeze; verify
the team Safe, ten real resolver-only wallets and funded Safe-owned subscription; deploy fresh
Sepolia contracts; record role/consumer/admin receipts and a real VRF fulfillment with focused
transaction smoke. Full local cross-layer normal/disputed/timeout/VOID/claim comparisons remain
whole-team acceptance work. Public hosted integration is the M4 stretch/M5 requirement.
