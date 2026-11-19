# M5 VRF Funding Preflight

November 19 follow-up: the [market 2 public lifecycle and cross-layer verification](../../../deployments/m5-sepolia-lifecycle-2026-11-19/cross-layer/README.md)
now records a successful real VRF callback, settlement/claims, and matching shared DB/API/hosted
read-only UI state for issue #56. The dated checks below describe this document's original
preflight or market 0 scope; they do not substitute for that new evidence.

Deployment and authority verification previously accepted any positive LINK balance as funded.
That could label a subscription ready even when its balance was below the reviewed reserve
for the intended callback gas and gas lane. Both checks now require a positive, explicit
minimum and reject balances below it. This is the preflight defect tracked as ECON-B2 in
Matthew's M5 supplement and relates to
[issue #56](https://github.com/yuddy-s/AC_ON-esports-prediction-market/issues/56).

## Configure the Reviewed Reserve

1. Confirm the coordinator, subscription, key hash, LINK billing and callback gas match the
   intended deployment. The current market fixes these settings at construction.
2. Review the current official Chainlink billing estimate for that callback budget and gas
   lane. Allow for concurrent requests and a buffer. Distinguish the minimum reserve from
   the eventual fulfillment charge.
3. Set `VRF_MINIMUM_LINK_BALANCE_WEI` in the private deployment environment, using integer
   LINK base units with 18 decimals. For example, 300 LINK is `300000000000000000000` base
   units. This is a unit-conversion example, not an automatic estimate or universal minimum.
4. Fund the reviewed subscription and rerun the deployment simulation or authority check.

`contracts/.env.example` deliberately defaults the minimum to zero. Missing or zero minimum
configuration blocks deployment; a positive balance below the chosen minimum also fails.
The helper validates the operator's threshold, not the accuracy of the selected estimate.

`VerifyAdministration.verify` now takes six arguments, with `minimumLinkBalance` last. The
exact invocation is updated in the [deployment runbook](../CONTRACT_DEPLOYMENT.md). Existing
five-argument invocations must be updated. This changes local deployment tooling only; the
production PredictionMarket ABI, deployed bytecode and immutable settings are unchanged.

## Local Regression Validation

From `contracts/`:

```bash
forge test --offline --match-contract DeploymentTest
forge fmt --check
python3 script/export_handoff.py --check
python3 script/pricing_reference.py --check
```

All six deployment tests pass. The new regression completes the mock Safe handoff and verifies
that zero configuration, a positive but insufficient balance and a balance one base unit below
the minimum fail; a balance exactly at the minimum passes. The existing role, consumer and
resolver-pool checks remain covered.

The full November 18 local contract rerun passed 120 tests, including three invariant campaigns
at 256 runs and depth 500. Its contract source and test fingerprints match this PR's tree;
the [validation record](../../../deployments/m5-vrf-funding-preflight/contract-validation.json)
retains the command, seed, counts and hashes. The full rerun is a local result, not a CI or
real Chainlink fulfillment claim.

## Recorded Live Funding Observations

The isolated Sepolia diagnostics used the same coordinator, key hash, 2,000,000 callback gas
and three confirmations. The subscription dashboard reported the following at the saved
November 17 ET observations:

| Diagnostic | Balance | Dashboard maximum reserve | Recorded fulfillment |
|---|---:|---:|---|
| LINK billing | 10 test LINK | 248.46718474763279 LINK | None observed |
| Native billing | 0.0015 Sepolia ETH | 1.4633045 ETH | None observed |

The [sanitized observation record](../../../deployments/m5-vrf-funding-preflight/funding-observations.json)
links each request and subscription. These dashboard values are dated estimates; recheck
the official service before choosing a reserve. The initial native deposit was based on an
incorrect reserve calculation and did not validate native fulfillment.

Both diagnostics remained pending and underfunded at the saved observation. No successful
callback has been established by this change. The observations identify a concrete funding
blocker but do not prove the complete historical cause of the original stalled requests.

## Remaining Public Acceptance

The existing market is LINK billed; adding Sepolia ETH to a subscription does not change that
billing mode. A native-billing market would require a contract change and fresh deployment.
Market 0 is already terminal VOID, so the requested live demonstration needs a fresh market.

After reviewing and supplying sufficient funding, record a real callback, the selected five
resolvers, three matching votes, settlement, claims and cross-layer accounting. Issue #56
remains open. This PR performs no new funding, market deployment or wallet transaction.
