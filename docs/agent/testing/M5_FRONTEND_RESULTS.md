# M5 Frontend And Browser Results

Owner: Adriel. Status: local and public Vercel results recorded November 18, 2026; hosted Vercel +
Render results recorded November 19, 2026. Public URL: https://acon-esports-market.vercel.app, built
with `VITE_API_URL=https://ac-on-esports-prediction-market.onrender.com` since November 19.
Never include wallet secrets, tokens or private dashboards in screenshots or traces.

## Read-Only Browser Journeys (Playwright)

`frontend/e2e/public-read.e2e.ts` covers what a visitor can do without a wallet. Each journey fails on
any console error, uncaught page error, failed request or HTTP status of 400 or above, so a CORS or
missing-asset failure on the hosted site is caught even when the page renders.

| Journey | Checks |
|---|---|
| Markets page | "Pick a side" heading, Sepolia network label, at least one contract market |
| Market page | Opens the first market; question, resolution panel, stored state and the connect-wallet trade prompt |
| Fixture catalog | "Match schedule" heading; selects **All** (the catalog opens on Upcoming) before checking fixtures |
| Portfolio | Asks for a wallet instead of showing positions |
| Header navigation | Markets, Fixtures and Portfolio links reach their pages |

### Hosted API mode (`PLAYWRIGHT_EXPECT_API=1`)

Added after the PR #60 review: the heading "Recent trades" also renders while loading and for an
unconfigured or wrong-deployment indexer, and a wrong-chain status is still HTTP 200, so the heading
alone proved nothing. In API mode the journeys now:

- **Market page:** open market 0, wait for `/api/v2/indexer/status` and `/api/v2/markets/0/history`,
  require HTTP success, require the status body to report Sepolia (11155111), the M4 market
  `0x03ae…10E9` and `configured: true`, require a row linking to each of market 0's six
  receipt-backed transactions (`frontend/e2e/deployment.ts`, each checked as a successful Sepolia
  receipt to the M4 market with `cast receipt`), and require no loading, unverified, hidden or
  unreachable message. The stale-worker notice is allowed: it keeps rows visible and only warns.
- **Fixture catalog:** wait for `/api/fixtures`, require HTTP success and the "FROM THE FIXTURE API"
  label, select **All**, then require one link per returned fixture, or the "No fixtures match this
  filter." empty state when the API returns none.

Responses are awaited before the final console/network error check, so a late failure cannot slip
past the end of the test.

### API-state regressions (`frontend/e2e/api-states.e2e.ts`)

Mocked responses (no chain or backend writes) for the states the review reproduced. They need a
build with `VITE_API_URL`, so they run in API mode and are skipped otherwise.

| Case | Mocked response | Expected |
|---|---|---|
| Wrong chain | status HTTP 200, `chain_id: 1` | Strict check rejects the body; "The indexer is on chain 1, but this page is on chain 11155111. Recent trades are hidden."; no trade rows |
| Wrong contract | status HTTP 200, another contract | Strict check rejects; "tracking a different PredictionMarket contract … hidden"; no rows |
| Unconfigured indexer | status HTTP 200, `configured: false` | Strict check rejects; "no active market deployment … hidden"; no rows |
| Unavailable history | history HTTP 503 | "Indexer API unreachable at …"; no rows |
| Completed-only catalog | two `completed` fixtures | Upcoming shows "No fixtures match this filter." with no links; **All** lists both |

## Wallet Failure Journeys (LOC-08)

`frontend/e2e/wallet-failures.e2e.ts` replaces MetaMask with a scripted EIP-1193 provider that never
signs: it rejects every transaction, signature and network-switch request with the standard code
4001 and forwards reads to a public Sepolia RPC. No key, wallet or transaction is involved.

| Journey | Checks |
|---|---|
| LOC-08a wrong network | Wallet on Ethereum mainnet (chain 1): the "Wrong network: your wallet is on chain 1, but this app uses Sepolia" bar appears and the faucet claim is disabled. Refusing **Switch to Sepolia** shows "Could not switch automatically. Choose Sepolia in your wallet." and writes stay disabled. |
| LOC-08b rejected request | Wallet on Sepolia: rejecting the faucet claim turns the button into **Retry claim** ("The last claim failed. Try again.") and no `eth_sendRawTransaction` leaves the page. |

The reverted-receipt case ("The transaction was mined but reverted. Your ACON and your position did
not change.") comes from the chain, not the wallet, so it stays covered by the `tradeStatus` unit
tests and by manual MetaMask runs.

## Runs

| Run | Environment | Result | Notes |
|---|---|---|---|
| FE-01 | Local production build (`vite build` + `vite preview`), M4 Sepolia contracts over the public Sepolia RPC, no backend; desktop Chrome and Pixel 7 profiles | pass, 10/10 (5 journeys x 2 profiles) | Mock fixture catalog, because no API is configured. The first run failed every journey on a missing favicon (FE-B1). |
| FE-02 | Public Vercel deployment https://acon-esports-market.vercel.app, contract reads only (no `VITE_API_URL`); desktop Chrome and Pixel 7 profiles | pass, 10/10 | Deployed with the Vercel CLI from this branch. Response headers confirmed: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`. Not yet Git-connected: needs the Vercel GitHub app on the repo. |
| FE-04 | Public Vercel deployment (same build as FE-02), all 14 tests (read-only + LOC-08) with two workers | fail, 12/14 | Both market-page journeys failed: the default Sepolia RPC (`11155111.rpc.thirdweb.com`) answered the burst of reads without CORS headers, so the browser blocked every read (FE-B2). LOC-08a/b passed 4/4 on their own. |
| FE-05 | Local production build with the FE-B2 fix; all 14 tests, two workers, run twice | pass, 14/14 both runs | No RPC or CORS errors. |
| FE-06 | Public Vercel redeployed November 18 with the FE-B2 fix (deployment `acon-esports-market-r3rzqwr8j`); all 14 tests, two workers, run twice | pass, 14/14 both runs | Live bundle confirmed to contain the fallback endpoints. No RPC or CORS errors. Closes FE-B2 on the public site. |
| FE-08 | Local production build after the PR #60 review fixes (no API); all journeys, desktop and Pixel 7 | pass, 14/14 (10 API-state regressions skipped: no `VITE_API_URL`) | Recorded November 19 on macOS. The local preview now binds `127.0.0.1`, because `localhost` resolved to `::1` and Playwright's server check never connected. |

## Hosted Results (Vercel + Render)

Kept separate from the frontend-only runs above. Frontend: Vercel production deployment from this
branch with `VITE_API_URL` set (deployment `acon-esports-market-6kqeo0dcz`, November 19, 2026). API:
https://ac-on-esports-prediction-market.onrender.com.

| Run | Check | Result | Notes |
|---|---|---|---|
| PUB-01 | API `/health`, `/api/indexer/status`, CORS, sample data | pass | Health OK with database available; status reports chain 11155111, contract `0x03ae…10E9` and ABI `PredictionMarket.721a6fef039a.4af9297937eb`, matching `deployments/sepolia-2026-11-02`. CORS allows `https://acon-esports-market.vercel.app` and not other origins. Market 0 projected as VOID with the same six trades as the chain. |
| FE-03 | First hosted run, `PLAYWRIGHT_EXPECT_API=1`, earlier assertions | 14/14 twice, **superseded** | Only checked the "Recent trades" heading and the absence of mock data, which the PR #60 review showed can pass without usable history. Kept for the record; FE-07 is the hosted acceptance result. |
| FE-07 | Hosted run with the strict API-mode assertions and the API-state regressions, desktop and Pixel 7 | **pass, 24/24, run twice** | 14 journeys (status body, all six market 0 receipts, API fixture catalog under All, LOC-08) plus 10 mocked regressions. No console, CORS or network errors. At run time (04:00 UTC) the indexer's last update was 03:37 UTC: rows were correct, with the stale-worker notice shown. |

A local build pointed at the Render API (`PLAYWRIGHT_API_URL=… PLAYWRIGHT_EXPECT_API=1`) passes the 10
regressions but cannot pass the strict real-data journeys: the API's CORS policy allows only the Vercel
origin, so the browser blocks reads from `127.0.0.1`. That is the intended policy, so hosted acceptance
is measured on the Vercel + Render pair (FE-07).

Indexer availability: the Render API and Supabase are hosted, but the indexer worker runs on a team
machine rather than as an always-on Render worker, to avoid hosting cost. When it is not running the
site shows "The indexer worker has not updated for over 2 minutes" and keeps the last indexed rows.

Commands (from `frontend/`, after `npx playwright install chromium` once, or set
`PLAYWRIGHT_CHANNEL=chrome` for an installed Chrome):

- Local build, no API: `npm run test:e2e`
- Public site, contract reads only: `PLAYWRIGHT_BASE_URL=https://acon-esports-market.vercel.app npm run test:e2e`
- Hosted acceptance: `PLAYWRIGHT_BASE_URL=https://acon-esports-market.vercel.app PLAYWRIGHT_EXPECT_API=1 npm run test:e2e`

## Unit Baseline

`npm test` 163 passed (19 files, including the new `config.test.ts` for FE-B2), `npm run typecheck`
clean, `npm run build` succeeded on this branch.

## Frontend Defects

Also recorded as M5-003 and M5-004 in [`M5_DEFECT_LOG.md`](M5_DEFECT_LOG.md).

| ID | Severity | Symptom and reproduction | Root cause | Fix | Regression test | Status |
|---|---|---|---|---|---|---|
| FE-B1 | P3 | Every page load logged `404 /favicon.ico`; the new browser journeys failed on it. | `index.html` declared no icon and the build shipped none. | Added `public/favicon.svg` and a `<link rel="icon">`. | All five journeys assert no HTTP errors; 10/10 pass after the fix. | fixed |
| FE-B2 | P2 | On the public site, a burst of contract reads (two Playwright workers opening market pages) made the default Sepolia RPC respond without CORS headers; the browser blocked every read and the market page could not load its data (FE-04). | The wagmi transport used only viem's built-in Sepolia endpoint (`http(undefined)`), so one rate-limited provider broke all reads. | Sepolia reads now use a `fallback` transport: optional `VITE_SEPOLIA_RPC_URL`, then keyless publicnode and dRPC endpoints, then the old default. | `config.test.ts` (endpoint order, dedupe, https only); full 14-test browser suite twice with no RPC errors, locally (FE-05) and on the redeployed public site (FE-06). | verified |
