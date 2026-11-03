import { isTradable, lmsrPrices } from "./lmsr";
import { MARKET_STATE } from "./predictionMarket";
import type { Market } from "./useMarkets";

// What the wallet holds in one market, read from the contract.
export interface Holding {
  yes: bigint;
  no: bigint;
  claimable: bigint;
  claimed: boolean;
}

export type ValueKind = "estimate" | "exact" | "claimed";

export interface PortfolioRow {
  market: Market;
  holding: Holding;
  // Base units. "estimate" = shares x current display price (open or
  // awaiting a result); "exact" = the contract's claimableAmount.
  value: bigint;
  valueKind: ValueKind;
  tradable: boolean;
  settled: boolean;
  canClaim: boolean;
}

export function isSettled(state: number): boolean {
  return state === MARKET_STATE.FINALIZED || state === MARKET_STATE.VOID;
}

// Shares x price without leaving integer base units (price rounded to 1e-9).
export function markToPrice(shares: bigint, price: number): bigint {
  const scaled = BigInt(Math.round(Math.min(1, Math.max(0, price)) * 1e9));
  return (shares * scaled) / 1_000_000_000n;
}

export function portfolioRow(market: Market, holding: Holding, nowSeconds: number): PortfolioRow {
  const settled = isSettled(market.state);
  const tradable = isTradable(market.state, market.tradingDeadline, nowSeconds);
  if (settled) {
    return {
      market,
      holding,
      value: holding.claimed ? 0n : holding.claimable,
      valueKind: holding.claimed ? "claimed" : "exact",
      tradable,
      settled,
      // A losing position still has to be claimed (for 0) to close it.
      canClaim: !holding.claimed && (holding.yes > 0n || holding.no > 0n),
    };
  }
  const prices = lmsrPrices(market.yesQuantity, market.noQuantity);
  return {
    market,
    holding,
    value: markToPrice(holding.yes, prices.yes) + markToPrice(holding.no, prices.no),
    valueKind: "estimate",
    tradable,
    settled,
    canClaim: false,
  };
}

// Rows for markets the wallet is in: shares held, or a settled claim
// (including ones already collected, so history does not vanish).
export function portfolioRows(markets: readonly Market[], holdings: readonly (Holding | undefined)[], nowSeconds: number): PortfolioRow[] {
  return markets
    .map((m, i) => ({ m, h: holdings[i] }))
    .filter(({ h }) => h !== undefined && (h.yes > 0n || h.no > 0n || h.claimed))
    .map(({ m, h }) => portfolioRow(m, h as Holding, nowSeconds))
    .sort((a, b) => Number(b.canClaim) - Number(a.canClaim) || Number(b.tradable) - Number(a.tradable) || Number(b.market.id - a.market.id));
}

export interface PortfolioTotals {
  openValue: bigint;
  claimable: bigint;
  markets: number;
}

export function portfolioTotals(rows: readonly PortfolioRow[]): PortfolioTotals {
  return {
    openValue: rows.filter((r) => r.valueKind === "estimate").reduce((sum, r) => sum + r.value, 0n),
    claimable: rows.filter((r) => r.valueKind === "exact").reduce((sum, r) => sum + r.value, 0n),
    markets: rows.filter((r) => r.valueKind !== "claimed").length,
  };
}

// Which state the page is in. Every branch renders something, so a connected
// wallet never sees a blank page (zero markets, read failures, loading).
export type PortfolioView =
  | { kind: "disconnected" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "no-markets" }
  | { kind: "no-positions" }
  | { kind: "positions" };

export function portfolioView(input: {
  connected: boolean;
  marketCount: number | undefined;
  marketsError: unknown;
  holdingsLoaded: boolean;
  holdingsError: unknown;
  rowCount: number;
}): PortfolioView {
  if (!input.connected) return { kind: "disconnected" };
  const failure = input.marketsError ?? input.holdingsError;
  if (failure) return { kind: "error", message: failure instanceof Error ? failure.message.split("\n")[0] : String(failure) };
  if (input.marketCount === undefined) return { kind: "loading" };
  if (input.marketCount === 0) return { kind: "no-markets" };
  if (!input.holdingsLoaded) return { kind: "loading" };
  return input.rowCount === 0 ? { kind: "no-positions" } : { kind: "positions" };
}
