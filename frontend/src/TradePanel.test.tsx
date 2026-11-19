import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Issue #53: an expired market whose stored state is still OPEN must render as closed and keep the
// buy/sell button disabled. Wallet and chain reads are stubbed; everything else is the real panel.

const DEADLINE = 1_000_000n;
const ONE = 10n ** 18n;
const chain = vi.hoisted(() => ({ now: 0, state: 0 }));
// A static render cannot click the Sell tab, so start the panel in the mode under test. Only the
// mode state is initialised with "buy"; React's real useState still runs.
const ui = vi.hoisted(() => ({ mode: "buy" as "buy" | "sell" }));

vi.mock("react", async (orig) => {
  const actual = await orig<typeof import("react")>();
  return { ...actual, useState: (init: unknown) => actual.useState(init === "buy" ? ui.mode : init) };
});

vi.mock("./config", async (orig) => ({
  ...(await orig<typeof import("./config")>()),
  PREDICTION_MARKET_ADDRESS: "0x03ae48f03C7822540a91DA2168602bd49dC510E9",
  ACON_TOKEN_ADDRESS: "0xf85b2278a810410c6AE0b7490d34671E0C8e6E90",
}));

vi.mock("./useNow", () => ({ useChainNowSeconds: () => chain.now }));
vi.mock("./useTradeFlow", () => ({ useTradeFlow: () => ({ status: { kind: "idle" }, trade: vi.fn(), reset: vi.fn() }) }));

vi.mock("wagmi", async () => {
  // The wallet is on the app's own chain (VITE_CHAIN may be anvil or sepolia locally).
  const { CHAIN } = await import("./config");
  return {
    useAccount: () => ({ address: "0x1111111111111111111111111111111111111111", isConnected: true, chainId: CHAIN.id }),
    useReadContract: ({ functionName, query }: { functionName: string; query?: { enabled?: boolean } }) => {
      if (functionName === "getMarket") return { data: { state: chain.state, tradingDeadline: DEADLINE } };
      // quoteBuy/quoteSell: the panel only asks for a quote while it thinks the market is tradable.
      return { data: query?.enabled === false ? undefined : 5n * ONE };
    },
    // ACON balance, allowance, YES shares, NO shares: enough for any trade.
    useReadContracts: () => ({ data: [1_000n * ONE, 1_000n * ONE, 50n * ONE, 50n * ONE] }),
  };
});

const { TradePanel } = await import("./TradePanel");

const render = () => renderToStaticMarkup(<TradePanel marketId={0n} />);
const tradeButton = (html: string) => html.match(/<button[^>]*class="btn-gold w-full[^>]*>.*?<\/button>/)?.[0] ?? "";

describe("TradePanel at the trading deadline (#53)", () => {
  beforeEach(() => {
    chain.state = 0; // stored state OPEN
    ui.mode = "buy";
  });

  it("before the deadline: quotes and enables the buy button", () => {
    chain.now = Number(DEADLINE) - 1;
    const html = render();
    expect(html).not.toContain("Trading is closed for this market.");
    expect(html).toContain("You pay at most");
    expect(tradeButton(html)).toMatch(/Buy/);
    expect(tradeButton(html)).not.toMatch(/disabled/);
  });

  for (const [label, now] of [
    ["exactly at the deadline", Number(DEADLINE)],
    ["after the deadline", Number(DEADLINE) + 3_600],
  ] as const) {
    it(`${label} with stored state still OPEN: shows trading closed and disables the button`, () => {
      chain.now = now;
      const html = render();
      expect(html).toContain("Trading is closed for this market.");
      expect(html).not.toContain("You pay at most");
      expect(tradeButton(html)).toMatch(/disabled/);
    });
  }

  describe("sell mode", () => {
    beforeEach(() => {
      ui.mode = "sell";
    });

    it("before the deadline: quotes proceeds and enables the sell button", () => {
      chain.now = Number(DEADLINE) - 1;
      const html = render();
      expect(html).not.toContain("Trading is closed for this market.");
      expect(html).toContain("You receive at least");
      expect(tradeButton(html)).toMatch(/Sell/);
      expect(tradeButton(html)).not.toMatch(/disabled/);
    });

    for (const [label, now] of [
      ["exactly at the deadline", Number(DEADLINE)],
      ["after the deadline", Number(DEADLINE) + 3_600],
    ] as const) {
      it(`${label} with stored state still OPEN: shows trading closed and disables the sell button`, () => {
        chain.now = now;
        const html = render();
        expect(html).toContain("Trading is closed for this market.");
        expect(html).not.toContain("You receive at least");
        expect(tradeButton(html)).toMatch(/Sell/);
        expect(tradeButton(html)).toMatch(/disabled/);
      });
    }
  });
});
