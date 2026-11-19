import { expect, test, type Page } from "@playwright/test";
import { indexerStatusProblems, MARKET_0_RECEIPTS, UNTRUSTED_HISTORY_TEXT } from "./deployment";

// Read-only public journeys: everything a visitor can do without connecting a wallet.
const EXPECT_API = process.env.PLAYWRIGHT_EXPECT_API === "1";

const isStatus = (url: string) => url.includes("/api/v2/indexer/status");
const isMarket0History = (url: string) => url.includes("/api/v2/markets/0/history");
const isFixtureList = (url: string) => url.includes("/api/fixtures?");

// Console errors and failed same-site or API requests fail the test (CORS failures show up here).
function watchForErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (msg) => {
    // HTTP errors are reported with their URL by the response listener below.
    if (msg.type() === "error" && !msg.text().startsWith("Failed to load resource")) {
      errors.push(`console: ${msg.text()}`);
    }
  });
  page.on("response", (res) => {
    if (res.status() >= 400) errors.push(`http ${res.status()}: ${res.url()}`);
  });
  page.on("pageerror", (err) => errors.push(`page: ${err.message}`));
  page.on("requestfailed", (req) => {
    const failure = req.failure()?.errorText ?? "";
    // Leaving a page aborts its in-flight RPC reads; that is not a failure.
    if (!failure.includes("ERR_ABORTED")) errors.push(`request: ${req.url()} ${failure}`);
  });
  return errors;
}

test("markets page lists contract markets on Sepolia", async ({ page }) => {
  const errors = watchForErrors(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Pick a side" })).toBeVisible();
  // The header shows the network label in a desktop and a mobile variant.
  await expect(page.getByText("SEPOLIA TESTNET").filter({ visible: true }).first()).toBeVisible();
  await expect(page.locator('a[href^="#/markets/"]').first()).toBeVisible();
  expect(errors).toEqual([]);
});

test("a market page shows its resolution and details without a wallet", async ({ page }) => {
  const errors = watchForErrors(page);
  await page.goto("/");
  // With the API, open market 0: its indexed history is pinned to known chain receipts.
  const market = EXPECT_API ? page.locator('a[href="#/markets/0"]') : page.locator('a[href^="#/markets/"]').first();
  await expect(market).toBeVisible();
  const status = EXPECT_API ? page.waitForResponse((r) => isStatus(r.url())) : null;
  const history = EXPECT_API ? page.waitForResponse((r) => isMarket0History(r.url())) : null;
  await market.click();
  await expect(page).toHaveURL(/#\/markets\/\d+$/);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText("Resolution", { exact: true })).toBeVisible();
  await expect(page.getByText("Stored state", { exact: true })).toBeVisible();
  await expect(page.getByText("Connect a wallet (top right) to trade this market.")).toBeVisible();
  if (status && history) {
    // A wrong-chain or wrong-contract indexer still answers HTTP 200, so check the body, then
    // require every receipt-backed row and no loading or untrusted-deployment message.
    const statusResponse = await status;
    expect(statusResponse.ok()).toBe(true);
    expect(indexerStatusProblems(await statusResponse.json())).toEqual([]);
    expect((await history).ok()).toBe(true);
    for (const { hash } of MARKET_0_RECEIPTS) {
      await expect(page.locator(`a[href$="/tx/${hash}"]`)).toBeVisible();
    }
    await expect(page.getByText(UNTRUSTED_HISTORY_TEXT)).toHaveCount(0);
  }
  expect(errors).toEqual([]);
});

test("fixture catalog loads", async ({ page }) => {
  const errors = watchForErrors(page);
  const list = EXPECT_API ? page.waitForResponse((r) => isFixtureList(r.url())) : null;
  await page.goto("/#/fixtures");
  await expect(page.getByRole("heading", { name: "Match schedule" })).toBeVisible();
  // The catalog opens on Upcoming; a healthy catalog may hold only completed matches.
  await page.getByRole("button", { name: "all", exact: true }).click();
  const links = page.locator('a[href^="#/fixtures/"]');
  if (list) {
    const response = await list;
    expect(response.ok()).toBe(true);
    const body = (await response.json()) as { items: unknown[] };
    await expect(page.getByText("FROM THE FIXTURE API")).toBeVisible();
    await expect(page.getByText(/mock fixtures/i)).toHaveCount(0);
    if (body.items.length > 0) {
      await expect(links).toHaveCount(body.items.length);
    } else {
      await expect(page.getByText("No fixtures match this filter.")).toBeVisible();
    }
  } else {
    await expect(links.first()).toBeVisible();
  }
  await expect(page.getByText(/Loading fixtures|Fixture catalog unavailable/)).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("portfolio asks for a wallet instead of showing positions", async ({ page }) => {
  const errors = watchForErrors(page);
  await page.goto("/#/portfolio");
  await expect(page.getByRole("heading", { name: "Your positions" })).toBeVisible();
  await expect(page.getByText("Connect a wallet (top right) to see your positions.")).toBeVisible();
  expect(errors).toEqual([]);
});

test("header navigation reaches every page", async ({ page }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation");
  await nav.getByRole("link", { name: "Fixtures" }).click();
  await expect(page.getByRole("heading", { name: "Match schedule" })).toBeVisible();
  await nav.getByRole("link", { name: "Portfolio" }).click();
  await expect(page.getByRole("heading", { name: "Your positions" })).toBeVisible();
  await nav.getByRole("link", { name: "Markets" }).click();
  await expect(page.getByRole("heading", { name: "Pick a side" })).toBeVisible();
});
