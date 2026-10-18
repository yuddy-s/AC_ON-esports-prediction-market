import { sepolia } from "wagmi/chains";
import { useReadContract } from "wagmi";
import {
  MARKET_STATES,
  PREDICTION_MARKET_ADDRESS,
  predictionMarketAbi,
} from "./predictionMarket";

function shortenAddress(address: string) {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export function MarketCard() {
  const { data, isLoading, error } = useReadContract({
    address: PREDICTION_MARKET_ADDRESS,
    abi: predictionMarketAbi,
    functionName: "getMarket",
    args: [0n],
    chainId: sepolia.id,
  });

  return (
    <section className="rounded-lg border border-neutral-700 bg-neutral-900 p-5">
      <p className="text-xs uppercase tracking-wide text-neutral-500">
        Market #0 · Ethereum Sepolia
      </p>

      {isLoading && <p className="mt-3 text-sm text-neutral-400">Loading market…</p>}
      {error && (
        <p className="mt-3 break-words text-sm text-red-400">
          Could not read market: {error.message.split("\n")[0]}
        </p>
      )}

      {data && (
        <div className="mt-3 flex flex-col gap-2">
          <h2 className="text-lg font-semibold text-neutral-100">{data[0]}</h2>
          <p className="text-sm text-neutral-400">
            Status:{" "}
            <span className="text-amber-300">
              {MARKET_STATES[Number(data[2])] ?? `Unknown (${data[2]})`}
            </span>
          </p>
          <p className="text-sm text-neutral-400">
            Trading deadline: {new Date(Number(data[1]) * 1000).toLocaleString()}
          </p>
          <p className="text-sm text-neutral-400">
            Creator: <span className="font-mono">{shortenAddress(data[3])}</span>
          </p>
          <a
            href={`https://sepolia.etherscan.io/address/${PREDICTION_MARKET_ADDRESS}`}
            target="_blank"
            rel="noreferrer"
            className="mt-1 text-sm text-amber-300 underline underline-offset-2"
          >
            View contract on Etherscan
          </a>
        </div>
      )}
    </section>
  );
}
