# M5 economics and integration evidence — November 18, 2026

Start with the [economic results report](../../docs/agent/testing/M5_ECONOMIC_RESULTS.md).
It distinguishes local regressions, real Sepolia receipts, shared Supabase with a local API/UI,
and the hosted acceptance and live VRF journey that remain pending.

## Recorded evidence

| Evidence | Scope |
|---|---|
| [Contract summary](contract-test-summary.json), [compressed raw result](contract-tests.json.gz), [run metadata](run-metadata.json) | 120 local tests; 256 fuzz runs; three invariant campaigns totaling 384,000 handler calls. The historical working tree included both fixes later split into #57 and #58. This is not a CI run or a fresh live VRF test. |
| [Pricing check](pricing-reference-check.json), [parameters](economic-parameters.json), [source/configuration](configuration-and-source-check.json), [format](format-check.json), [handoff](handoff-check.json) | Recorded pricing, bounded-domain configuration and source comparison checks. |
| [Indexer regressions](indexer-regression-check.json) | Three focused tests on local SQLite; separate from the shared PostgreSQL verification below. |
| [Accounting reconciliation](accounting-reconciliation.json) | Exact bond, VOID liability, payout, surplus and wallet arithmetic from the three saved receipt observations in the November 2 deployment directory. Duplicate and repeat checks were read-only simulations. |
| [Public trade reconciliation](public-trade-reconciliation.json) | Five historical buys and one sell; quotes, slippage, transfers, token balances, positions, quantities, collateral and indexed/API history match. No new trades were submitted. |
| [Shared catch-up](supabase-catchup-verification.json), [repeat sync](live-indexer-idempotence.json) | Corrected local #57 handler applied nine confirmed missing events to the real shared Supabase database; no deletes or rebuild. Repeat synchronization processed no duplicates. |
| [Local API results](supabase-local-api-verification.json), [chain recheck](market-0-chain-recheck.json), [market UI](supabase-market-0-ui.png) | Seven API endpoints, current receipt/accounting reads and an observed local frontend. They do not verify a hosted Render/Vercel deployment. Small historical values are rounded in the UI; exact comparisons use integer API/receipt values. |
| [Final verification summary](final-verification-summary.json) | Dated consistency-check summary; not an additional integration run. |
| [VRF recheck](../sepolia-2026-11-17-vrf-diagnostic/RECHECK-2026-11-18.md) | No callbacks; underfunded subscriptions and current reserve-estimation inputs. Issue #56 remains open. |

These are immutable-in-time observations, not a promise that the local services remain running.
The report records a later local timeout, worker exit and successful restart/recheck. Private
database backups, credentials, wallet-operation pages, exploratory funding routes and Word
generation files are excluded from this evidence bundle.

## Inspect and reproduce

From the repository root:

```bash
python3 deployments/m5-economics-2026-11-18/reconcile-accounting.py
gzip -dc deployments/m5-economics-2026-11-18/contract-tests.json.gz > /tmp/acon-m5-contract-tests.json
python3 -m json.tool /tmp/acon-m5-contract-tests.json > /dev/null
```

The offline script checks the saved receipt observations only; it makes no network requests
and does not establish the separately recorded database/API/UI result. Reproducing the local
contract run requires the source hashes and both fixes identified in `run-metadata.json`;
the evidence branch itself contains no #58 production or deployment-tool changes.
