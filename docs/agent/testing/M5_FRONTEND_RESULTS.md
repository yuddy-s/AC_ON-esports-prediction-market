# M5 Frontend And Browser Results

Owner: Adriel. Status: local and public Vercel results recorded November 18, 2026. Public URL:
https://acon-esports-market.vercel.app (contract reads only until the Render API is configured). Never include wallet secrets, tokens or private
dashboards in screenshots or traces.

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

| Run | Environment | Result | Notes |
|---|---|---|---|
| FE-01 | Local production build (`vite build` + `vite preview`), M4 Sepolia contracts over the public Sepolia RPC, no backend; desktop Chrome and Pixel 7 profiles | pass, 10/10 (5 journeys x 2 profiles) | Mock fixture catalog, because no API is configured. The first run failed every journey on a missing favicon (FE-B1). |
| FE-02 | Public Vercel deployment https://acon-esports-market.vercel.app, contract reads only (no `VITE_API_URL`); desktop Chrome and Pixel 7 profiles | pass, 10/10 | Deployed with the Vercel CLI from this branch. Response headers confirmed: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`. Not yet Git-connected: needs the Vercel GitHub app on the repo. |
| FE-03 | Public Vercel + Render API | pending | Run with `PLAYWRIGHT_EXPECT_API=1`; needed before ECON-05/ECON-06 move to pass. |

Command: `cd frontend && PLAYWRIGHT_CHANNEL=chrome npm run test:e2e` (installed Chrome) or
`npx playwright install chromium` once, then `npm run test:e2e`.

## Unit Baseline

`npm test` 159 passed (18 files), `npm run typecheck` clean, `npm run build` succeeded on this branch.

## Frontend Defects

Also recorded as M5-003 in [`M5_DEFECT_LOG.md`](M5_DEFECT_LOG.md).

| ID | Severity | Symptom and reproduction | Root cause | Fix | Regression test | Status |
|---|---|---|---|---|---|---|
| FE-B1 | P3 | Every page load logged `404 /favicon.ico`; the new browser journeys failed on it. | `index.html` declared no icon and the build shipped none. | Added `public/favicon.svg` and a `<link rel="icon">`. | All five journeys assert no HTTP errors; 10/10 pass after the fix. | fixed |
