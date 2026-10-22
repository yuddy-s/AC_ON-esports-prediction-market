import { describe, expect, it } from "vitest";
import type { IndexedTrade } from "./indexerApi";
import { describeIndexerLag, toTradeRows } from "./tradeRows";

const trader = "0x70997970c51812dc3a010c7d01b50e0d17dc79c8";

function trade(block: number, logIndex: number, outcome: number, shares: string, cost: string): IndexedTrade {
  return {
    market_id: 0,
    trader,
    outcome,
    shares,
    cost,
    yes_quantity: "0",
    no_quantity: "0",
    block_number: block,
    transaction_hash: `0x${block.toString(16).padStart(64, "0")}`,
    log_index: logIndex,
  };
}

describe("toTradeRows", () => {
  const trades = [
    trade(527, 2, 0, "10000000000000000000", "5249584441082326050"),
    trade(584, 1, 1, "5000000000000000000", "2312800000000000000"),
  ];

  it("lists the newest trade first", () => {
    expect(toTradeRows(trades).map((r) => r.block)).toEqual([584, 527]);
  });

  it("orders trades in the same block by log index", () => {
    const rows = toTradeRows([trade(600, 1, 0, "1", "1"), trade(600, 3, 1, "1", "1")]);
    expect(rows.map((r) => r.key.split(":")[1])).toEqual(["3", "1"]);
  });

  it("formats side, shares and cost from 1e18 base units", () => {
    const [newest, oldest] = toTradeRows(trades);
    expect(newest).toMatchObject({ side: "NO", shares: "5", cost: "2.31", trader: "0x7099...79c8" });
    expect(oldest).toMatchObject({ side: "YES", shares: "10", cost: "5.24" });
  });

  it("marks the connected wallet's trades regardless of address case", () => {
    expect(toTradeRows(trades, "0x70997970C51812dc3A010C7d01b50e0d17dc79C8")[0].isYou).toBe(true);
    expect(toTradeRows(trades, "0x0000000000000000000000000000000000000001")[0].isYou).toBe(false);
    expect(toTradeRows(trades)[0].isYou).toBe(false);
  });

  it("does not change the input order", () => {
    toTradeRows(trades);
    expect(trades[0].block_number).toBe(527);
  });
});

describe("describeIndexerLag", () => {
  it("shows the last safe block and lag", () => {
    expect(describeIndexerLag(2538, 2)).toBe("Indexed up to block 2538 (2 blocks behind the chain).");
    expect(describeIndexerLag(100, 1)).toBe("Indexed up to block 100 (1 block behind the chain).");
  });

  it("handles an indexer that has not started", () => {
    expect(describeIndexerLag(null, null)).toBe("Indexer has not processed any blocks yet.");
  });
});
