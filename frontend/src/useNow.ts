import { useEffect, useState } from "react";
import { useBlock } from "wagmi";
import { CHAIN } from "./config";

// Current Unix time in seconds, refreshed on an interval so deadline checks
// update without a page reload.
export function useNowSeconds(intervalMs = 5_000): number {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now() / 1000), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

// The chain's clock: the contract compares deadlines with block.timestamp,
// not the browser's time. They match on Sepolia, but local Anvil demos
// fast-forward time for 24-hour challenge and 48-hour vote windows.
export function chainNow(blockTimestamp: bigint | undefined, sampledAtMs: number, wallNowMs: number): number {
  if (blockTimestamp === undefined) return wallNowMs / 1000;
  return Number(blockTimestamp) + Math.max(0, wallNowMs - sampledAtMs) / 1000;
}

export function useChainNowSeconds(intervalMs = 5_000): number {
  const wall = useNowSeconds(intervalMs);
  const block = useBlock({ chainId: CHAIN.id, query: { refetchInterval: 15_000 } });
  return chainNow(block.data?.timestamp, block.dataUpdatedAt, wall * 1000);
}
