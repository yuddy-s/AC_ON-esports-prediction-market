import { defineConfig, devices } from "@playwright/test";

// Read-only browser journeys (M5). No wallet and no transactions: MetaMask writes stay manual.
//
//   PLAYWRIGHT_BASE_URL=https://<deployment>.vercel.app npm run test:e2e   # public site
//   npm run test:e2e                                                        # local production build
//
// The local run builds against the public M4 Sepolia contracts with no backend, so the fixture
// catalog uses the bundled mock data. Set PLAYWRIGHT_EXPECT_API=1 when the target has the Render
// API configured to also require indexed history. PLAYWRIGHT_CHANNEL=chrome uses an installed
// Chrome instead of a downloaded browser.
const baseURL = process.env.PLAYWRIGHT_BASE_URL;
const channel = process.env.PLAYWRIGHT_CHANNEL;

const SEPOLIA_M4 = {
  VITE_CHAIN: "sepolia",
  VITE_PREDICTION_MARKET_ADDRESS: "0x03ae48f03C7822540a91DA2168602bd49dC510E9",
  VITE_ACON_TOKEN_ADDRESS: "0xf85b2278a810410c6AE0b7490d34671E0C8e6E90",
  VITE_DEMO_MARKET_ID: "0",
  VITE_API_URL: "",
  VITE_FIXTURE_SOURCE: "mock",
};

export default defineConfig({
  testDir: "./e2e",
  testMatch: /.*\.e2e\.ts/,
  timeout: 60_000,
  expect: { timeout: 20_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: baseURL ?? "http://127.0.0.1:4173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], channel } },
    { name: "mobile", use: { ...devices["Pixel 7"], channel } },
  ],
  webServer: baseURL
    ? undefined
    : {
        command: "npm run build && npm run preview -- --port 4173 --strictPort",
        url: "http://127.0.0.1:4173",
        timeout: 180_000,
        reuseExistingServer: !process.env.CI,
        env: SEPOLIA_M4,
      },
});
