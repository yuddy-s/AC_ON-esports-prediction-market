import { API_URL } from "./config";

// Read-only client for Yudhveer's FastAPI indexer endpoints. The backend is a
// derived cache: the chain stays authoritative, so these are only used to
// show when a mined trade has reached the indexed projection.

export interface IndexedTrade {
  market_id: number;
  trader: string;
  outcome: number;
  shares: string;
  cost: string;
  yes_quantity: string;
  no_quantity: string;
  block_number: number;
  transaction_hash: string;
  log_index: number;
}

export interface IndexerStatus {
  configured: boolean;
  chain_id: number;
  contract_address: string | null;
  latest_observed_block: number | null;
  last_safe_block: number | null;
  lag_blocks: number | null;
  updated_at: string | null;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { signal });
  if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
  return (await response.json()) as T;
}

// An empty list means "not indexed yet", not "failed".
export async function fetchTradesByTransaction(hash: string, signal?: AbortSignal): Promise<IndexedTrade[]> {
  const body = await getJson<{ items: IndexedTrade[] }>(`/api/trades/by-transaction/${hash}`, signal);
  return body.items;
}

export function fetchIndexerStatus(signal?: AbortSignal): Promise<IndexerStatus> {
  return getJson<IndexerStatus>("/api/indexer/status", signal);
}

interface TradePage {
  items: IndexedTrade[];
  total: number;
}

// The API pages oldest-first, so read the total, then fetch the last `count`.
export async function fetchRecentMarketTrades(
  marketId: bigint,
  count: number,
  signal?: AbortSignal,
): Promise<{ trades: IndexedTrade[]; total: number }> {
  const path = `/api/markets/${marketId}/trades`;
  const first = await getJson<TradePage>(`${path}?limit=${count}&offset=0`, signal);
  if (first.total <= count) return { trades: first.items, total: first.total };
  const last = await getJson<TradePage>(`${path}?limit=${count}&offset=${first.total - count}`, signal);
  return { trades: last.items, total: last.total };
}
