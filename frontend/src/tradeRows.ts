import { formatTokenAmount, shortenAddress } from "./format";
import type { IndexedTrade } from "./indexerApi";
import { OUTCOME } from "./predictionMarket";
import { parseBaseUnits } from "./tradeMath";

export interface TradeRow {
  key: string;
  block: number;
  trader: string;
  isYou: boolean;
  side: "YES" | "NO";
  shares: string;
  cost: string;
  transactionHash: string;
}

// Indexed trades (oldest first from the API) -> display rows, newest first.
export function toTradeRows(trades: readonly IndexedTrade[], account?: string): TradeRow[] {
  const you = account?.toLowerCase();
  return [...trades]
    .sort((a, b) => b.block_number - a.block_number || b.log_index - a.log_index)
    .map((trade) => ({
      key: `${trade.transaction_hash}:${trade.log_index}`,
      block: trade.block_number,
      trader: shortenAddress(trade.trader),
      isYou: you !== undefined && trade.trader.toLowerCase() === you,
      side: trade.outcome === OUTCOME.YES ? "YES" : "NO",
      shares: formatTokenAmount(parseBaseUnits(trade.shares)),
      cost: formatTokenAmount(parseBaseUnits(trade.cost)),
      transactionHash: trade.transaction_hash,
    }));
}

// "Indexed up to block 2538 (2 blocks behind)"; the default worker waits for
// 2 confirmations, so a small lag is normal.
export function describeIndexerLag(lastSafeBlock: number | null, lagBlocks: number | null): string {
  if (lastSafeBlock === null) return "Indexer has not processed any blocks yet.";
  const lag = lagBlocks ?? 0;
  return `Indexed up to block ${lastSafeBlock} (${lag} block${lag === 1 ? "" : "s"} behind the chain).`;
}
