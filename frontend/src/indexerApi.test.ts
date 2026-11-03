import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchTradesByTransaction, type IndexedTrade } from "./indexerApi";

const sell: IndexedTrade = {
  event: "SellExecuted",
  kind: "SELL",
  market_id: 7,
  trader: "0x3333333333333333333333333333333333333333",
  outcome: 0,
  shares: "200000000000000000",
  amount: "100000000000000000",
  cost: null,
  proceeds: "100000000000000000",
  yes_quantity: "800000000000000000",
  no_quantity: "0",
  block_number: 120,
  transaction_hash: `0x${"ab".repeat(32)}`,
  log_index: 2,
};

afterEach(() => vi.unstubAllGlobals());

describe("M4 transaction polling", () => {
  it("finds a SellExecuted event through market history", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ items: [sell], total: 1 }))));

    const trades = await fetchTradesByTransaction(7n, sell.transaction_hash.toUpperCase());

    expect(trades).toEqual([sell]);
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain("/api/v2/markets/7/history");
    expect(String(vi.mocked(fetch).mock.calls[0][0])).not.toContain("/api/trades/by-transaction");
  });

  it("returns an empty list while the transaction is not indexed", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ items: [], total: 0 }))));
    await expect(fetchTradesByTransaction(7n, sell.transaction_hash)).resolves.toEqual([]);
  });
});
