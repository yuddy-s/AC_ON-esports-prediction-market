import { expect, test, type Page } from "@playwright/test";

// Read-only public journeys: everything a visitor can do without connecting a wallet.
const EXPECT_API = process.env.PLAYWRIGHT_EXPECT_API === "1";

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
  const first = page.locator('a[href^="#/markets/"]').first();
  await expect(first).toBeVisible();
  await first.click();
  await expect(page).toHaveURL(/#\/markets\/\d+$/);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText("Resolution", { exact: true })).toBeVisible();
  await expect(page.getByText("Stored state", { exact: true })).toBeVisible();
  await expect(page.getByText("Connect a wallet (top right) to trade this market.")).toBeVisible();
  if (EXPECT_API) {
    await expect(page.getByText("Recent trades", { exact: true })).toBeVisible();
  }
  expect(errors).toEqual([]);
});

test("fixture catalog loads", async ({ page }) => {
  const errors = watchForErrors(page);
  await page.goto("/#/fixtures");
  await expect(page.getByRole("heading", { name: "Match schedule" })).toBeVisible();
  await expect(page.locator('a[href^="#/fixtures/"]').first()).toBeVisible();
  if (EXPECT_API) {
    await expect(page.getByText(/mock fixtures/i)).toHaveCount(0);
  }
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
