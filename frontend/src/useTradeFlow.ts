import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Address } from "viem";
import { simulateContract, waitForTransactionReceipt, writeContract } from "wagmi/actions";
import { API_URL, CHAIN } from "./config";
import { describeError, isUserRejection } from "./errors";
import { fetchIndexerStatus, fetchTradesByTransaction } from "./indexerApi";
import { aconTokenAbi, predictionMarketAbi, type Outcome } from "./predictionMarket";
import type { IndexerWait, TradeStatus } from "./tradeStatus";
import { config } from "./wagmi";

export interface BuyRequest {
  account: Address;
  market: Address;
  token: Address;
  marketId: bigint;
  outcome: Outcome;
  shares: bigint;
  maxCost: bigint;
  needsApproval: boolean;
}

const INDEXER_POLL_MS = 2_000;
const INDEXER_TIMEOUT_MS = 3 * 60_000;

export function useTradeFlow() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<TradeStatus>({ kind: "idle" });
  const runId = useRef(0);

  const buy = useCallback(
    async (request: BuyRequest) => {
      const run = ++runId.current;
      const update = (next: TradeStatus) => {
        if (runId.current === run) setStatus(next);
      };
      try {
        if (request.needsApproval) {
          // Approve exactly maxCost, not an unlimited allowance.
          update({ kind: "approve-wallet" });
          const approveHash = await writeContract(config, {
            address: request.token,
            abi: aconTokenAbi,
            functionName: "approve",
            args: [request.market, request.maxCost],
            chainId: CHAIN.id,
          });
          update({ kind: "approve-pending", hash: approveHash });
          const approval = await waitForTransactionReceipt(config, { hash: approveHash, chainId: CHAIN.id });
          if (approval.status !== "success") {
            update({ kind: "error", message: "The ACON approval transaction reverted." });
            return;
          }
        }

        // Simulate first so contract errors (slippage, deadline, balance)
        // show before the wallet prompt, decoded by name.
        update({ kind: "buy-wallet" });
        const { request: buyCall } = await simulateContract(config, {
          account: request.account,
          address: request.market,
          abi: predictionMarketAbi,
          functionName: "buy",
          args: [request.marketId, request.outcome, request.shares, request.maxCost],
          chainId: CHAIN.id,
        });
        const hash = await writeContract(config, buyCall);
        update({ kind: "submitted", hash });

        const receipt = await waitForTransactionReceipt(config, { hash, chainId: CHAIN.id });
        void queryClient.invalidateQueries();
        if (receipt.status !== "success") {
          update({ kind: "reverted", hash });
          return;
        }
        update({
          kind: "mined",
          hash,
          blockNumber: receipt.blockNumber,
          indexer: API_URL ? { state: "waiting", lastSafeBlock: null } : { state: "not-configured" },
        });
      } catch (error) {
        update(isUserRejection(error) ? { kind: "rejected" } : { kind: "error", message: describeError(error) });
      }
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
  useEffect(() => {
    if (!minedHash || minedBlock === undefined) return;
    const controller = new AbortController();
    const startedAt = Date.now();
    let timer: ReturnType<typeof setTimeout>;

    const setIndexer = (indexer: IndexerWait) =>
      setStatus((current) => (current.kind === "mined" && current.hash === minedHash ? { ...current, indexer } : current));

    const poll = async () => {
      try {
        const [trades, indexerStatus] = await Promise.all([
          fetchTradesByTransaction(minedHash, controller.signal),
          fetchIndexerStatus(controller.signal),
        ]);
        if (trades.length > 0) {
          setStatus((current) =>
            current.kind === "mined" && current.hash === minedHash
              ? { kind: "indexed", hash: minedHash, blockNumber: minedBlock, trade: trades[0] }
              : current,
          );
          void queryClient.invalidateQueries();
          return;
        }
        setIndexer({ state: "waiting", lastSafeBlock: indexerStatus.last_safe_block });
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
  }, [minedHash, minedBlock, queryClient]);

  return { status, buy, reset };
}
