import type { IndexedTrade } from "./indexerApi";
import { lmsrPrices } from "./lmsr";
import { OUTCOME } from "./predictionMarket";
import { parseBaseUnits } from "./tradeMath";

// One point per indexed trade: the YES price right after it, from the
// outstanding quantities the TradeExecuted event recorded. Point 0 is the
// market's opening price (no shares outstanding = 50%).
export interface PricePoint {
  index: number;
  yes: number;
  trade: {
    side: "YES" | "NO";
    shares: bigint;
    block: number;
    transactionHash: string;
  } | null;
}

export function toPriceHistory(trades: readonly IndexedTrade[]): PricePoint[] {
  const ordered = [...trades].sort((a, b) => a.block_number - b.block_number || a.log_index - b.log_index);
  const points: PricePoint[] = [{ index: 0, yes: 0.5, trade: null }];
  ordered.forEach((t, i) => {
    points.push({
      index: i + 1,
      yes: lmsrPrices(parseBaseUnits(t.yes_quantity), parseBaseUnits(t.no_quantity)).yes,
      trade: {
        side: t.outcome === OUTCOME.YES ? "YES" : "NO",
        shares: parseBaseUnits(t.shares),
        block: t.block_number,
        transactionHash: t.transaction_hash,
      },
    });
  });
  return points;
}

// Index of the point nearest to a fractional x position (0..points-1).
export function nearestPoint(count: number, x: number): number {
  return Math.min(count - 1, Math.max(0, Math.round(x)));
}

// SVG path for a step line: the price holds flat until the next trade.
export function stepPath(points: readonly { x: number; y: number }[]): string {
  if (points.length === 0) return "";
  let d = `M${points[0].x},${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    d += `H${points[i].x}V${points[i].y}`;
  }
  return d;
}
