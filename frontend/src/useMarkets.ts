import type { Address } from "viem";
import { useReadContract, useReadContracts } from "wagmi";
import { CHAIN, PREDICTION_MARKET_ADDRESS } from "./config";
import { predictionMarketAbi } from "./predictionMarket";

export interface Market {
  id: bigint;
  question: string;
  tradingDeadline: bigint;
  state: number;
  creator: Address;
  yesQuantity: bigint;
  noQuantity: bigint;
}

type MarketTuple = readonly [string, bigint, number, Address, bigint, bigint];

export function toMarket(id: bigint, [question, tradingDeadline, state, creator, yesQuantity, noQuantity]: MarketTuple): Market {
  return { id, question, tradingDeadline, state, creator, yesQuantity, noQuantity };
}

// The M3 contract has no list function: read marketCount, then getMarket for
// each id. Fine for a class-sized number of markets.
export function useMarkets() {
  const enabled = PREDICTION_MARKET_ADDRESS !== undefined;
  const count = useReadContract({
    address: PREDICTION_MARKET_ADDRESS,
    abi: predictionMarketAbi,
    functionName: "marketCount",
    chainId: CHAIN.id,
    query: { enabled, refetchInterval: 15_000 },
  });
  const ids = Array.from({ length: Number(count.data ?? 0n) }, (_, i) => BigInt(i));
  const markets = useReadContracts({
    contracts: ids.map((id) => ({
      address: PREDICTION_MARKET_ADDRESS,
      abi: predictionMarketAbi,
      functionName: "getMarket" as const,
      args: [id] as const,
      chainId: CHAIN.id,
    })),
    allowFailure: false,
    query: { enabled: enabled && ids.length > 0, refetchInterval: 10_000 },
  });

  return {
    markets: markets.data ? markets.data.map((tuple, i) => toMarket(ids[i], tuple as MarketTuple)) : count.data === 0n ? [] : undefined,
    isLoading: count.isLoading || markets.isLoading,
    error: count.error ?? markets.error,
  };
}

export function useMarket(id: bigint) {
  const read = useReadContract({
    address: PREDICTION_MARKET_ADDRESS,
    abi: predictionMarketAbi,
    functionName: "getMarket",
    args: [id],
    chainId: CHAIN.id,
    query: { enabled: PREDICTION_MARKET_ADDRESS !== undefined, refetchInterval: 10_000 },
  });
  return { market: read.data ? toMarket(id, read.data) : undefined, isLoading: read.isLoading, error: read.error };
}
