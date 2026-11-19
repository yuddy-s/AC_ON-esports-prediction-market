import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { API_URL, CHAIN, PREDICTION_MARKET_ADDRESS } from "./config";
import { fetchIndexerStatus, fetchTradesByTransaction } from "./indexerApi";
import { indexerDeploymentProblem, indexerIsStale } from "./indexerHealth";
import type { IndexerWait, TradeStatus } from "./tradeStatus";
import { executeTrade, type TradeRequest } from "./tradeExecution";
export type { TradeRequest } from "./tradeExecution";

const INDEXER_POLL_MS = 2_000;
const INDEXER_TIMEOUT_MS = 3 * 60_000;

export function useTradeFlow() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<TradeStatus>({ kind: "idle" });
  const runId = useRef(0);

  const trade = useCallback(
    async (request: TradeRequest) => {
      const run = ++runId.current;
      const update = (next: TradeStatus) => {
        if (runId.current === run) setStatus(next);
      };
      await executeTrade(request, update, () => {
        void queryClient.invalidateQueries();
      });
    },
    [queryClient],
  );

  const reset = useCallback(() => {
    runId.current++;
    setStatus({ kind: "idle" });
  }, []);

  // After mining, poll the backend until the trade appears in the indexed
  // projection. An empty result means "not yet", not "failed".
  const minedHash = status.kind === "mined" && status.indexer.state !== "not-configured" ? status.hash : undefined;
  const minedBlock = status.kind === "mined" ? status.blockNumber : undefined;
  const minedMarketId = status.kind === "mined" ? status.marketId : undefined;
  useEffect(() => {
    if (!minedHash || minedBlock === undefined || minedMarketId === undefined) return;
    const controller = new AbortController();
    const startedAt = Date.now();
    let timer: ReturnType<typeof setTimeout>;

    const setIndexer = (indexer: IndexerWait) =>
      setStatus((current) => (current.kind === "mined" && current.hash === minedHash ? { ...current, indexer } : current));

    const poll = async () => {
      try {
        const [trades, indexerStatus] = await Promise.all([
          fetchTradesByTransaction(minedMarketId, minedHash, controller.signal),
          fetchIndexerStatus(controller.signal),
        ]);
        const deploymentProblem = indexerDeploymentProblem(indexerStatus, CHAIN.id, PREDICTION_MARKET_ADDRESS);
        if (deploymentProblem) {
          // A different deployment will never index this trade: stop waiting.
          setIndexer({ state: "not-tracking", detail: deploymentProblem.replace(/\.$/, "") });
          return;
        } else if (trades.length > 0) {
          setStatus((current) =>
            current.kind === "mined" && current.hash === minedHash
              ? { kind: "indexed", hash: minedHash, blockNumber: minedBlock, trade: trades[0] }
              : current,
          );
          void queryClient.invalidateQueries();
          return;
        } else if (indexerIsStale(indexerStatus)) {
          setIndexer({ state: "stale", lastSafeBlock: indexerStatus.last_safe_block });
        } else {
          setIndexer({ state: "waiting", lastSafeBlock: indexerStatus.last_safe_block });
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        setIndexer({ state: "unavailable", detail: error instanceof Error ? error.message : String(error) });
      }
      if (Date.now() - startedAt > INDEXER_TIMEOUT_MS) {
        setIndexer({ state: "timed-out" });
        return;
      }
      timer = setTimeout(poll, INDEXER_POLL_MS);
    };
    void poll();

    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [minedHash, minedBlock, minedMarketId, queryClient]);

  return { status, trade, reset };
}
