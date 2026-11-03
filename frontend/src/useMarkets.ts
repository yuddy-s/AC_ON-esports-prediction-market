import type { Address, Hex } from "viem";
import { useReadContract, useReadContracts } from "wagmi";
import { CHAIN, PREDICTION_MARKET_ADDRESS } from "./config";
import { predictionMarketAbi } from "./predictionMarket";

export interface Market {
  id: bigint;
  fixtureKey: Hex;
  question: string;
  tradingDeadline: bigint;
  state: number;
  creator: Address;
  yesQuantity: bigint;
  noQuantity: bigint;
  collateralBalance: bigint;
}

// The registered match behind a market: YES is Team A, NO is Team B.
export interface MarketTeams {
  teamA: string;
  teamB: string;
  gameId: string;
  scheduledStart: bigint;
  evidenceURI: string;
}

const read = { address: PREDICTION_MARKET_ADDRESS, abi: predictionMarketAbi, chainId: CHAIN.id } as const;

// The contract has no list function: read marketCount, then getMarket and
// the market's fixture for each id. Fine for a class-sized number of markets.
export function useMarkets() {
  const enabled = PREDICTION_MARKET_ADDRESS !== undefined;
  const count = useReadContract({ ...read, functionName: "marketCount", query: { enabled, refetchInterval: 15_000 } });
  const ids = Array.from({ length: Number(count.data ?? 0n) }, (_, i) => BigInt(i));
  const markets = useReadContracts({
    contracts: ids.map((id) => ({ ...read, functionName: "getMarket" as const, args: [id] as const })),
    allowFailure: false,
    query: { enabled: enabled && ids.length > 0, refetchInterval: 10_000 },
  });
  // Mapped call lists lose wagmi's per-call typing; the shapes follow the ABI.
  const list = markets.data as Market[] | undefined;
  const teams = useFixtures(list?.map((m) => m.fixtureKey) ?? []);

  return {
    markets: list ?? (count.data === 0n ? [] : undefined),
    teams,
    isLoading: count.isLoading || markets.isLoading,
    error: count.error ?? markets.error,
    refetch: () => void (count.error ? count.refetch() : markets.refetch()),
  };
}

export function useMarket(id: bigint) {
  const market = useReadContract({
    ...read,
    functionName: "getMarket",
    args: [id],
    query: { enabled: PREDICTION_MARKET_ADDRESS !== undefined, refetchInterval: 10_000 },
  });
  const teams = useFixtures(market.data ? [market.data.fixtureKey] : []);
  return {
    market: market.data ? ({ ...market.data } as Market) : undefined,
    teams: market.data ? teams.get(market.data.fixtureKey) : undefined,
    isLoading: market.isLoading,
    error: market.error,
  };
}

interface FixtureStruct {
  data: { teamAName: string; teamBName: string; gameId: string; scheduledStart: bigint; evidenceURI: string };
}

function useFixtures(keys: Hex[]): Map<Hex, MarketTeams> {
  const fixtures = useReadContracts({
    contracts: keys.map((key) => ({ ...read, functionName: "getFixture" as const, args: [key] as const })),
    allowFailure: false,
    query: { enabled: keys.length > 0, staleTime: 60_000 },
  });
  const map = new Map<Hex, MarketTeams>();
  (fixtures.data as FixtureStruct[] | undefined)?.forEach((f, i) => {
    map.set(keys[i], {
      teamA: f.data.teamAName,
      teamB: f.data.teamBName,
      gameId: f.data.gameId,
      scheduledStart: f.data.scheduledStart,
      evidenceURI: f.data.evidenceURI,
    });
  });
  return map;
}
