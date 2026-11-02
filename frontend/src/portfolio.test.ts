import { describe, expect, it } from "vitest";
import { markToPrice, portfolioRow, portfolioRows, portfolioTotals, portfolioView, type Holding } from "./portfolio";
import { MARKET_STATE } from "./predictionMarket";
import type { Market } from "./useMarkets";

const E18 = 10n ** 18n;
const NOW = 1_000_000;

function market(id: bigint, state: number, extra: Partial<Market> = {}): Market {
  return {
    id,
    fixtureKey: "0x01",
    question: `Market ${id}`,
    tradingDeadline: BigInt(NOW + 3_600),
    state,
    creator: "0x0000000000000000000000000000000000000001",
    yesQuantity: 0n,
    noQuantity: 0n,
    collateralBalance: 0n,
    ...extra,
  };
}

const holding = (extra: Partial<Holding> = {}): Holding => ({ yes: 0n, no: 0n, claimable: 0n, claimed: false, ...extra });

describe("markToPrice", () => {
  it("multiplies shares by a price in integer base units", () => {
    expect(markToPrice(10n * E18, 0.5)).toBe(5n * E18);
    expect(markToPrice(3n * E18, 0)).toBe(0n);
  });

  it("clamps prices outside 0..1", () => {
    expect(markToPrice(E18, 1.2)).toBe(E18);
    expect(markToPrice(E18, -0.1)).toBe(0n);
  });
});

describe("portfolioRow", () => {
  it("estimates an open position at the current price", () => {
    const row = portfolioRow(market(1n, MARKET_STATE.OPEN), holding({ yes: 10n * E18, no: 4n * E18 }), NOW);
    // Equal outstanding quantities -> 50/50 prices.
    expect(row).toMatchObject({ value: 7n * E18, valueKind: "estimate", tradable: true, canClaim: false });
  });

  it("uses the contract's exact claimable amount once settled", () => {
    const row = portfolioRow(market(2n, MARKET_STATE.FINALIZED), holding({ yes: 5n * E18, claimable: 5n * E18 }), NOW);
    expect(row).toMatchObject({ value: 5n * E18, valueKind: "exact", canClaim: true, settled: true });
  });

  it("still offers the claim for a losing position, which pays 0 but closes it", () => {
    const row = portfolioRow(market(3n, MARKET_STATE.FINALIZED), holding({ no: 2n * E18, claimable: 0n }), NOW);
    expect(row).toMatchObject({ value: 0n, canClaim: true });
  });

  it("marks a collected payout as claimed with no value left", () => {
    const row = portfolioRow(market(4n, MARKET_STATE.VOID), holding({ claimed: true }), NOW);
    expect(row).toMatchObject({ value: 0n, valueKind: "claimed", canClaim: false });
  });

  it("is not tradable past the deadline even while OPEN", () => {
    expect(portfolioRow(market(5n, MARKET_STATE.OPEN), holding({ yes: E18 }), NOW + 3_600).tradable).toBe(false);
  });
});

describe("portfolioRows and totals", () => {
  const markets = [
    market(0n, MARKET_STATE.FINALIZED),
    market(1n, MARKET_STATE.OPEN),
    market(2n, MARKET_STATE.OPEN),
    market(3n, MARKET_STATE.VOID),
  ];
  const holdings = [
    holding({ yes: 5n * E18, claimable: 5n * E18 }),
    holding({ yes: 2n * E18 }),
    holding(),
    holding({ claimed: true }),
  ];

  it("lists only markets the wallet is in, claimable first", () => {
    const rows = portfolioRows(markets, holdings, NOW);
    expect(rows.map((r) => r.market.id)).toEqual([0n, 1n, 3n]);
  });

  it("skips markets whose holdings have not loaded", () => {
    expect(portfolioRows(markets, [undefined, holdings[1]], NOW).map((r) => r.market.id)).toEqual([1n]);
  });

  it("totals open estimates and exact claimables separately", () => {
    expect(portfolioTotals(portfolioRows(markets, holdings, NOW))).toEqual({ openValue: E18, claimable: 5n * E18, markets: 2 });
  });
});

describe("portfolioView", () => {
  const base = { connected: true, marketCount: 3, marketsError: null, holdingsLoaded: true, holdingsError: null, rowCount: 2 };

  it("asks to connect a wallet first", () => {
    expect(portfolioView({ ...base, connected: false })).toEqual({ kind: "disconnected" });
  });

  it("says there are no markets when the deployment has none (holdings reads never run)", () => {
    expect(portfolioView({ ...base, marketCount: 0, holdingsLoaded: false, rowCount: 0 })).toEqual({ kind: "no-markets" });
  });

  it("reports a failed market read instead of rendering nothing", () => {
    const error = new Error("HTTP request failed.\nURL: http://127.0.0.1:8545");
    const view = portfolioView({ ...base, marketCount: undefined, marketsError: error, holdingsLoaded: false });
    expect(view).toEqual({ kind: "error", message: "HTTP request failed." });
  });

  it("reports a failed position read", () => {
    expect(portfolioView({ ...base, holdingsLoaded: false, holdingsError: new Error("timeout") }).kind).toBe("error");
  });

  it("is loading until markets and holdings arrive", () => {
    expect(portfolioView({ ...base, marketCount: undefined, holdingsLoaded: false }).kind).toBe("loading");
    expect(portfolioView({ ...base, holdingsLoaded: false }).kind).toBe("loading");
  });

  it("separates no positions from positions", () => {
    expect(portfolioView({ ...base, rowCount: 0 }).kind).toBe("no-positions");
    expect(portfolioView(base).kind).toBe("positions");
  });
});
