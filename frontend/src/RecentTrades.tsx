import { useQuery } from "@tanstack/react-query";
import { useAccount } from "wagmi";
import { API_URL, DEMO_MARKET_ID, EXPLORER_URL } from "./config";
import { fetchIndexerStatus, fetchRecentMarketTrades } from "./indexerApi";
import { describeIndexerLag, toTradeRows } from "./tradeRows";

const SHOWN = 10;

// Read-only view of the backend's indexed projection: trades appear here once
// the indexer has stored the mined TradeExecuted event (chain stays authoritative).
export function RecentTrades() {
  const { address } = useAccount();

  const trades = useQuery({
    queryKey: ["indexed-trades", DEMO_MARKET_ID.toString()],
    queryFn: ({ signal }) => fetchRecentMarketTrades(DEMO_MARKET_ID, SHOWN, signal),
    enabled: API_URL !== "",
    refetchInterval: 3_000,
  });
  const status = useQuery({
    queryKey: ["indexer-status"],
    queryFn: ({ signal }) => fetchIndexerStatus(signal),
    enabled: API_URL !== "",
    refetchInterval: 3_000,
  });

  if (!API_URL) return null;
  const rows = trades.data ? toTradeRows(trades.data.trades, address) : [];

  return (
    <section className="rounded-lg border border-neutral-700 bg-neutral-900 p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-400">Recent trades</h2>
        <span className="text-xs text-neutral-500">from the indexer API</span>
      </div>

      {status.data && (
        <p className="mt-1 text-xs text-neutral-500">{describeIndexerLag(status.data.last_safe_block, status.data.lag_blocks)}</p>
      )}

      {trades.isLoading && <p className="mt-3 text-sm text-neutral-400">Loading trades…</p>}
      {trades.isError && (
        <p className="mt-3 text-sm text-red-400">
          Indexer API unreachable at {API_URL}. Trades on the chain are unaffected.
        </p>
      )}
      {trades.data && rows.length === 0 && <p className="mt-3 text-sm text-neutral-400">No trades indexed yet.</p>}

      {rows.length > 0 && (
        <table className="mt-3 w-full text-left text-sm">
          <thead className="text-xs text-neutral-500">
            <tr>
              <th className="pb-2 font-normal">Block</th>
              <th className="pb-2 font-normal">Trader</th>
              <th className="pb-2 font-normal">Side</th>
              <th className="pb-2 text-right font-normal">Shares</th>
              <th className="pb-2 text-right font-normal">Cost (ACON)</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {rows.map((row) => (
              <tr key={row.key} className="border-t border-neutral-800">
                <td className="py-1.5">
                  {EXPLORER_URL ? (
                    <a href={`${EXPLORER_URL}/tx/${row.transactionHash}`} target="_blank" rel="noreferrer" className="underline underline-offset-2">
                      {row.block}
                    </a>
                  ) : (
                    row.block
                  )}
                </td>
                <td className="py-1.5">
                  {row.trader}
                  {row.isYou && <span className="ml-1 font-sans text-xs text-amber-300">(you)</span>}
                </td>
                <td className={`py-1.5 ${row.side === "YES" ? "text-emerald-300" : "text-rose-300"}`}>{row.side}</td>
                <td className="py-1.5 text-right">{row.shares}</td>
                <td className="py-1.5 text-right">{row.cost}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {trades.data && trades.data.total > rows.length && (
        <p className="mt-2 text-xs text-neutral-500">
          Showing the latest {rows.length} of {trades.data.total} trades.
        </p>
      )}
    </section>
  );
}
