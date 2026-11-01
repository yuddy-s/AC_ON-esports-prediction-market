# Contract verification record

Status: **current product consolidated and locally tested on 2026-11-01; ABI/economic review and fresh deployment pending**.
Source/dependency/ABI/runtime-template digests are in
[`deployments/build.json`](../../../deployments/build.json).
This record covers Benny's contract slice. The [M4 milestone test plan](../milestones/MILESTONE_4.md#full-documented-test-plan)
also requires frontend, backend, oracle/indexer and cross-layer evidence from their owners.

## Results

| Check | Local result |
|---|---|
| Solidity formatting | `forge fmt --check` passed |
| Production compilation | Solc 0.8.24, optimizer 200, `via_ir=true`; the current `script/Deploy.s.sol` compiles |
| Full Foundry suite | **105 passed, 0 failed, 0 skipped** across eight suites |
| Lifecycle tests | 20 lifecycle, 23 resolver, 18 security/accounting, 5 deployment-helper tests |
| Token/trading/math tests | 14 real-token market integration, 4 ACON, 20 LMSR deterministic/fuzz, 1 grouped invariant suite |
| Fuzz/invariant runs | 256 runs per fuzz test; grouped LMSR invariant 256 runs × 500 calls = 128,000 calls, zero reverts |
| Local Anvil | **Six journeys, 101 successful transactions**, real ACON/pricing/registry/market, explicit mock coordinator |
| ABI/event handoff | Four exact JSON ABI exports, source/dependency/runtime-template hashes, generated reference and required event examples validate |
| Static analysis | Slither 0.11.3: **0 high, 2 medium, 14 low**; `--fail-high` passes with findings retained below |

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
| MarketPricing | 4,180 | 24,576 |
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
2. Challenge NO, request randomness, retry after 30 minutes, ignore the superseded callback,
   install the current committee, three YES votes, refund the changed-outcome bond, claim.
3. Propose VOID, wait the same challenge period, combine YES and NO holdings into one payout.
4. Seven days without a proposal, permissionless resolver selection, quorum and claim.
5. No first-round quorum, replacement committee, second voting deadline, VOID and claim.
6. Insufficient resolver pool, fixed seven-day formation deadline, VOID and claim.

Final market collateral, challenge escrow and the contract's ACON balance all reconcile to zero
after these journeys' claims/surplus withdrawals. This is a contract-level transaction test, not
frontend/backend integration or proof of real Chainlink/Safe behavior.

## Security and correctness coverage

| Area | Exercised behavior |
|---|---|
| Fixtures | Registrar permission; exact key/team order; immutable funded metadata; revision-race rejection; one market; failed funding rollback; deadline margin; historical registrar conflicts |
| Trades | YES/NO positions and exact token changes; bounded sizes/quantities; actual intervening-trade buy/sell slippage; no trade at/after deadline; no unowned sells; tiny sell rejection |
| Lifecycle | Immutable authorized proposal; 24-hour edge; no self/duplicate challenge; separate bond; late proposal cannot race no-proposal expiry; unchallenged finalize |
| Resolver | All conflicts; distinct frozen candidates; shortages/replenishment; retries/failures; request ID zero; cross-market identity; unauthorized/stale/duplicate/malformed/late callbacks; preserved snapshot/deadline |
| Voting | Selected-only, once per round, strict 48-hour edge; YES/NO/VOID quorum; fresh replacement and reuse fallback; formation expiry and second-round VOID |
| Funds | Winning/VOID claims; combined odd-unit rounding and ceiling reserves; losing zero claim; duplicate/no-position rejection; creator-only reserved surplus; market isolation |
| Adversarial interactions | False-returning and fee-like transfers; rollback of token/position/claim/bond/vote effects; incoming/outgoing/coordinator reentry; invalid raw enum calldata |
| Administration | Two-step transfer removes former admin; no accidental default-admin renunciation/duplication; narrow-role recovery; no admin rewrite of a proposal or withdrawal of user claims |

The mixed-market fuzz test performs 16 randomized buys/sells across two markets and two wallets,
checks quantities and balances after each action, then tests all outcome kinds, claims and surplus
withdrawals. It is useful integration evidence, **not** Matthew's independent stateful economic
proof over the complete supported domain. The retained 128,000-call invariant harness concerns
pure M3 LMSR buys; do not describe it as a full M4 lifecycle invariant campaign.

### Coverage measurement

The consolidated coverage run passed **104 tests**, excluding only the production runtime-size
assertion from the 105-test normal suite. All market tests, including the real-ACON regression
suite, exercise the same current `PredictionMarket`; there is no separate old-market implementation.

```bash
FOUNDRY_OUT=out/coverage FOUNDRY_CACHE_PATH=cache/coverage \
  forge coverage --ir-minimum --exclude-tests --no-match-coverage '^script/' \
  --no-match-test testProductionContractsFitEip170RuntimeLimit \
  --report summary --report lcov --report-file cache/verification/lcov.info
```

| Production file | Lines | Statements | Branches | Functions |
|---|---:|---:|---:|---:|
| MarketAccess | 97.44% (38/39) | 89.74% | 72.73% | 100% |
| MarketPricing | 100% (12/12) | 94.44% | 75% | 100% |
| PredictionMarket | 98.47% (386/392) | 95.66% | 83.84% | 97.73% |
| ResolverRegistry | 90% (18/20) | 90.48% | 75% | 75% |
| All production source | 97.74% (519/531) | 94.96% | 81.54% | 95.77% |

These are the measured current run's counts, not promised future thresholds. Minimum-IR source maps
can be imprecise and its bytecode differs from production; the normal test suite and exporter
still enforce production runtime size. Scripts/tests/dependencies are excluded from the table.
LCOV is retained under the ignored cache and uploaded in CI.

## Slither finding review

Install into a local virtual environment using `contracts/security-requirements.txt`, then run
from `contracts/` with its executable on PATH:

```bash
FOUNDRY_OUT=out/security FOUNDRY_CACHE_PATH=cache/security \
  slither . --filter-paths 'lib/|test/|script/' --fail-high \
  --json cache/verification/slither.json
```

Use an unused report filename when rerunning; Slither does not overwrite existing reports.
The current report is `cache/verification/slither.json`. Output/cache isolation keeps
Slither's `forge clean` away from normal and coverage artifacts. The scan covers all current
first-party production contracts; it excludes library, test and script findings.

| Finding | Count/severity | Review and evidence |
|---|---|---|
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
The commands have been exercised locally; **a hosted GitHub Actions run is still pending publication**.

Before M4 release: record Matthew's economics/payout approval and consumer ABI freeze; verify
the team Safe, ten real resolver-only wallets and funded Safe-owned subscription; deploy fresh
Sepolia contracts; record role/consumer/admin receipts and a real VRF fulfillment with focused
transaction smoke. Full local cross-layer normal/disputed/timeout/VOID/claim comparisons remain
whole-team acceptance work. Public hosted integration is the M4 stretch/M5 requirement.
