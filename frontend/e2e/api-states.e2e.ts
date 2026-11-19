import { expect, test, type Page, type Route } from "@playwright/test";
import { indexerStatusProblems, M4_MARKET_ADDRESS, SEPOLIA_CHAIN_ID } from "./deployment";

// Regression coverage for PR #60 review: API states that answer without an HTTP or console error
// but must not count as healthy indexed history or a broken catalog. Responses are mocked in the
// browser, so these need a build with VITE_API_URL set (the hosted site, or a local build with
// PLAYWRIGHT_API_URL). They never write to the chain or the backend.
const API_BUILD = process.env.PLAYWRIGHT_EXPECT_API === "1" || Boolean(process.env.PLAYWRIGHT_API_URL);
test.skip(!API_BUILD, "needs a build with VITE_API_URL (set PLAYWRIGHT_EXPECT_API=1 or PLAYWRIGHT_API_URL)");

const CORS = { "access-control-allow-origin": "*", "content-type": "application/json" };

function fulfillJson(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, headers: CORS, body: JSON.stringify(body) });
}

function statusBody(overrides: Record<string, unknown>) {
  return {
    configured: true,
    chain_id: SEPOLIA_CHAIN_ID,
    contract_address: M4_MARKET_ADDRESS.toLowerCase(),
    latest_observed_block: 100,
    last_safe_block: 98,
    lag_blocks: 2,
    updated_at: new Date().toISOString(),
    authoritative: false,
    ...overrides,
  };
}

async function mockStatus(page: Page, body: unknown) {
  await page.route((url) => url.pathname === "/api/v2/indexer/status", (route) => fulfillJson(route, body));
}

const txLinks = (page: Page) => page.locator('a[href*="/tx/0x"]');

const WRONG_DEPLOYMENTS = [
  {
    name: "wrong chain",
    body: statusBody({ chain_id: 1 }),
    message: `The indexer is on chain 1, but this page is on chain ${SEPOLIA_CHAIN_ID}. Recent trades are hidden.`,
  },
  {
    name: "wrong contract",
    body: statusBody({ contract_address: "0x000000000000000000000000000000000000dead" }),
    message: "The indexer is tracking a different PredictionMarket contract. Recent trades are hidden.",
  },
  {
    name: "unconfigured indexer",
    body: statusBody({ configured: false, contract_address: null }),
    message: "The indexer has no active market deployment. Recent trades are hidden.",
  },
];

for (const { name, body, message } of WRONG_DEPLOYMENTS) {
  test(`indexed history is hidden and rejected for a ${name} (HTTP 200)`, async ({ page }) => {
    // The strict hosted check must reject this body even though it is a successful response.
    expect(indexerStatusProblems(body)).not.toEqual([]);
    await mockStatus(page, body);
    await page.goto("/#/markets/0");
    await expect(page.getByText(message)).toBeVisible();
    await expect(page.getByText("Recent trades", { exact: true })).toBeVisible();
    await expect(txLinks(page)).toHaveCount(0);
  });
}

test("unavailable trade history shows the API error and no rows", async ({ page }) => {
  await page.route(
    (url) => url.pathname === "/api/v2/markets/0/history",
    (route) => fulfillJson(route, { detail: "unavailable" }, 503),
  );
  await page.goto("/#/markets/0");
  await expect(page.getByText(/Indexer API unreachable at /)).toBeVisible();
  await expect(txLinks(page)).toHaveCount(0);
});

function completedFixture(id: number, teams: [string, string]) {
  const [a, b] = teams;
  return {
    id,
    provider_id: "acon-e2e",
    game_id: "cs2",
    external_match_id: `e2e-${id}`,
    scheduled_start: "2026-11-01T18:00:00Z",
    match_status: "completed",
    team_a_id: a.toLowerCase(),
    team_a_name: a,
    team_b_id: b.toLowerCase(),
    team_b_name: b,
    evidence_url: `https://example.org/acon-e2e/${id}`,
    evidence_hash: `0x${id.toString(16).padStart(64, "0")}`,
    source_updated_at: "2026-11-01T20:00:00Z",
    imported_at: "2026-11-01T20:05:00Z",
    latest_result: null,
    registration_request_status: null,
    authoritative: false,
  };
}

test("a completed-only catalog is a valid empty Upcoming view and lists every match under All", async ({ page }) => {
  const items = [completedFixture(9001, ["Alpha", "Bravo"]), completedFixture(9002, ["Charlie", "Delta"])];
  await page.route(
    (url) => url.pathname === "/api/fixtures",
    (route) => fulfillJson(route, { items, total: items.length, limit: 100, offset: 0 }),
  );
  await page.goto("/#/fixtures");
  await expect(page.getByRole("heading", { name: "Match schedule" })).toBeVisible();
  await expect(page.getByText("No fixtures match this filter.")).toBeVisible();
  const links = page.locator('a[href^="#/fixtures/"]');
  await expect(links).toHaveCount(0);
  await page.getByRole("button", { name: "all", exact: true }).click();
  await expect(links).toHaveCount(items.length);
  await expect(page.getByText("Alpha")).toBeVisible();
});
