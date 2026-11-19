# M5 Frontend And Browser Results

Owner: Adriel. Status: local and public Vercel results recorded November 18, 2026. Public URL:
https://acon-esports-market.vercel.app (contract reads only until the Render API is configured).
Never include wallet secrets, tokens or private dashboards in screenshots or traces.

## Read-Only Browser Journeys (Playwright)

`frontend/e2e/public-read.e2e.ts` covers what a visitor can do without a wallet. Each journey fails on
any console error, uncaught page error, failed request or HTTP status of 400 or above, so a CORS or
missing-asset failure on the hosted site is caught even when the page renders.

| Journey | Checks |
|---|---|
| Markets page | "Pick a side" heading, Sepolia network label, at least one contract market |
| Market page | Opens the first market; question, resolution panel, stored state and the connect-wallet trade prompt |
| Fixture catalog | "Match schedule" heading and at least one fixture |
| Portfolio | Asks for a wallet instead of showing positions |
| Header navigation | Markets, Fixtures and Portfolio links reach their pages |

With `PLAYWRIGHT_EXPECT_API=1` the market page must also show indexed recent trades and the fixture
catalog must come from the backend instead of mock data. Use that mode once the Render API is live.

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
| FE-05 | Local production build with the FE-B2 fix; all 14 tests, two workers, run twice | pass, 14/14 both runs | No RPC or CORS errors. Redeploy to Vercel and rerun on the public site to close FE-B2 there. |
| FE-03 | Public Vercel + Render API | pending | Run with `PLAYWRIGHT_EXPECT_API=1`; needed before ECON-05/ECON-06 move to pass. |

Command: `cd frontend && PLAYWRIGHT_CHANNEL=chrome npm run test:e2e` (installed Chrome) or
`npx playwright install chromium` once, then `npm run test:e2e`. Add
`PLAYWRIGHT_BASE_URL=https://acon-esports-market.vercel.app` to target the public site.

## Unit Baseline

`npm test` 163 passed (19 files, including the new `config.test.ts` for FE-B2), `npm run typecheck`
clean, `npm run build` succeeded on this branch.

## Frontend Defects

Also recorded as M5-003 and M5-004 in [`M5_DEFECT_LOG.md`](M5_DEFECT_LOG.md).

| ID | Severity | Symptom and reproduction | Root cause | Fix | Regression test | Status |
|---|---|---|---|---|---|---|
| FE-B1 | P3 | Every page load logged `404 /favicon.ico`; the new browser journeys failed on it. | `index.html` declared no icon and the build shipped none. | Added `public/favicon.svg` and a `<link rel="icon">`. | All five journeys assert no HTTP errors; 10/10 pass after the fix. | fixed |
| FE-B2 | P2 | On the public site, a burst of contract reads (two Playwright workers opening market pages) made the default Sepolia RPC respond without CORS headers; the browser blocked every read and the market page could not load its data (FE-04). | The wagmi transport used only viem's built-in Sepolia endpoint (`http(undefined)`), so one rate-limited provider broke all reads. | Sepolia reads now use a `fallback` transport: optional `VITE_SEPOLIA_RPC_URL`, then keyless publicnode and dRPC endpoints, then the old default. | `config.test.ts` (endpoint order, dedupe, https only); full 14-test browser suite twice with no RPC errors (FE-05). | fixed (local); verify on Vercel after redeploy |
