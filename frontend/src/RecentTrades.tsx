import { useQuery } from "@tanstack/react-query";
import { useAccount } from "wagmi";
import { API_URL, CHAIN, EXPLORER_URL, PREDICTION_MARKET_ADDRESS } from "./config";
import { fetchIndexerStatus, fetchRecentMarketTrades } from "./indexerApi";
import { indexerDeploymentProblem, indexerIsStale } from "./indexerHealth";
import { describeIndexerLag, toTradeRows } from "./tradeRows";
import { Panel, PanelTitle } from "./ui";

const SHOWN = 10;

// Read-only view of the backend's indexed projection: trades appear here once
// the indexer has stored the mined TradeExecuted event (chain stays authoritative).
export function RecentTrades({ marketId }: { marketId: bigint }) {
  const { address } = useAccount();

  const trades = useQuery({
    queryKey: ["indexed-trades", marketId.toString()],
    queryFn: ({ signal }) => fetchRecentMarketTrades(marketId, SHOWN, signal),
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
  const deploymentProblem = status.data
    ? indexerDeploymentProblem(status.data, CHAIN.id, PREDICTION_MARKET_ADDRESS)
    : null;
  const trustedStatus = status.data && !status.isError && !deploymentProblem;
  const rows = trustedStatus && trades.data ? toTradeRows(trades.data.trades, address) : [];

  return (
    <Panel>
      <PanelTitle tag="Tape" title="Recent trades" aside={<span className="font-mono text-[11px] text-dust">FROM THE INDEXER API</span>} />

      {trustedStatus && (
        <p className="mt-2 font-mono text-xs text-dust">{describeIndexerLag(status.data.last_safe_block, status.data.lag_blocks)}</p>
      )}
      {trustedStatus && indexerIsStale(status.data) && (
        <p className="mt-2 text-sm text-gold">The indexer worker has not updated for over 2 minutes. Recent trades may be missing.</p>
      )}
      {status.isLoading && <p className="mt-3 text-sm text-sand">Checking indexer deployment…</p>}
      {status.isError && <p className="mt-3 text-sm text-signal">Cannot verify the indexer deployment. Recent trades are hidden.</p>}
      {deploymentProblem && <p className="mt-3 text-sm text-signal">{deploymentProblem} Recent trades are hidden.</p>}

      {trades.isLoading && <p className="mt-3 text-sm text-sand">Loading trades…</p>}
      {trades.isError && (
        <p className="mt-3 text-sm text-signal">
          Indexer API unreachable at {API_URL}. Trades on the chain are unaffected.
        </p>
      )}
      {trustedStatus && trades.data && rows.length === 0 && <p className="mt-3 text-sm text-sand">No trades indexed yet.</p>}

      {rows.length > 0 && (
        <table className="mt-3 w-full text-left text-sm">
          <thead className="label">
            <tr>
              <th className="pb-2 font-normal">Block</th>
              <th className="pb-2 font-normal">Trader</th>
              <th className="pb-2 font-normal">Side</th>
              <th className="pb-2 text-right font-normal">Shares</th>
              <th className="pb-2 text-right font-normal">Cost (ACON)</th>
            </tr>
          </thead>
          <tbody className="num font-mono">
            {rows.map((row) => (
              <tr key={row.key} className="border-t border-bronze/30">
                <td className="py-1.5">
                  {EXPLORER_URL ? (
                    <a href={`${EXPLORER_URL}/tx/${row.transactionHash}`} target="_blank" rel="noreferrer" className="link">
                      {row.block}
                    </a>
                  ) : (
                    row.block
                  )}
                </td>
                <td className="py-1.5">
                  {row.trader}
                  {row.isYou && <span className="ml-1 font-sans text-xs text-gold">(you)</span>}
                </td>
                <td className={`py-1.5 ${row.side === "YES" ? "text-gold" : "text-signal-soft"}`}>{row.side}</td>
                <td className="py-1.5 text-right">{row.shares}</td>
                <td className="py-1.5 text-right">{row.cost}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {trustedStatus && trades.data && trades.data.total > rows.length && (
        <p className="mt-2 text-xs text-dust">
          Showing the latest {rows.length} of {trades.data.total} trades.
        </p>
      )}
    </Panel>
  );
}
