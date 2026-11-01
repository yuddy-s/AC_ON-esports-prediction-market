import { describe, expect, it } from "vitest";
import type { IndexedTrade } from "./indexerApi";
import { nearestPoint, stepPath, toPriceHistory } from "./priceHistory";

const E18 = 10n ** 18n;

function trade(block: number, logIndex: number, outcome: number, shares: number, yesQty: number, noQty: number): IndexedTrade {
  return {
    market_id: 3,
    trader: "0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
    outcome,
    shares: (BigInt(shares) * E18).toString(),
    cost: "1",
    yes_quantity: (BigInt(yesQty) * E18).toString(),
    no_quantity: (BigInt(noQty) * E18).toString(),
    block_number: block,
    transaction_hash: `0x${block.toString(16).padStart(64, "0")}`,
    log_index: logIndex,
  };
}

describe("toPriceHistory", () => {
  it("starts at 50% before any trade", () => {
    expect(toPriceHistory([])).toEqual([{ index: 0, yes: 0.5, trade: null }]);
  });

  it("uses the quantities recorded after each trade", () => {
    const [, first, second] = toPriceHistory([trade(10, 0, 0, 70, 70, 0), trade(13, 0, 1, 10, 70, 10)]);
    expect(first.yes).toBeCloseTo(0.802, 3);
    expect(second.yes).toBeCloseTo(0.769, 3);
    expect(second.trade).toMatchObject({ side: "NO", shares: 10n * E18, block: 13 });
  });

  it("orders by block, then log index, whatever order the API returns", () => {
    const points = toPriceHistory([trade(20, 1, 1, 5, 10, 10), trade(20, 0, 0, 10, 10, 5), trade(5, 3, 0, 10, 10, 0)]);
    expect(points.map((p) => p.trade && `${p.trade.block}:${p.trade.side}`)).toEqual([null, "5:YES", "20:YES", "20:NO"]);
  });
});

describe("nearestPoint", () => {
  it("rounds to the closest point and clamps to the ends", () => {
    expect(nearestPoint(5, 1.4)).toBe(1);
    expect(nearestPoint(5, 1.6)).toBe(2);
    expect(nearestPoint(5, -3)).toBe(0);
    expect(nearestPoint(5, 99)).toBe(4);
  });
});

describe("stepPath", () => {
  it("holds each price flat until the next point", () => {
    expect(stepPath([{ x: 0, y: 50 }, { x: 10, y: 20 }, { x: 20, y: 30 }])).toBe("M0,50H10V20H20V30");
  });

  it("is empty with no points", () => {
    expect(stepPath([])).toBe("");
  });
});
