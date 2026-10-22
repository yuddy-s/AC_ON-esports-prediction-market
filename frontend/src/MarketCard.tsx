import { useReadContract } from "wagmi";
import {
  CHAIN,
  DEMO_MARKET_ID,
  EXPLORER_URL,
  PREDICTION_MARKET_ADDRESS,
} from "./config";
import { formatPercent, formatTokenAmount, shortenAddress } from "./format";
import { isTradable, lmsrPrices } from "./lmsr";
import { MARKET_STATES, predictionMarketAbi } from "./predictionMarket";
import { useNowSeconds } from "./useNow";

export function MarketCard() {
  const now = useNowSeconds();
  const { data, isLoading, error } = useReadContract({
    address: PREDICTION_MARKET_ADDRESS,
    abi: predictionMarketAbi,
    functionName: "getMarket",
    args: [DEMO_MARKET_ID],
    chainId: CHAIN.id,
    query: { enabled: PREDICTION_MARKET_ADDRESS !== undefined, refetchInterval: 10_000 },
  });

  return (
    <section className="rounded-lg border border-neutral-700 bg-neutral-900 p-5">
      <p className="text-xs uppercase tracking-wide text-neutral-500">
        Market #{DEMO_MARKET_ID.toString()} · {CHAIN.name}
      </p>

      {!PREDICTION_MARKET_ADDRESS && (
        <p className="mt-3 text-sm text-red-400">
          VITE_PREDICTION_MARKET_ADDRESS is not set (see frontend/.env.example).
        </p>
      )}
      {isLoading && <p className="mt-3 text-sm text-neutral-400">Loading market…</p>}
      {error && (
        <p className="mt-3 break-words text-sm text-red-400">
          Could not read market: {error.message.split("\n")[0]}
        </p>
      )}

      {data && <MarketDetails market={data} now={now} />}
    </section>
  );
}

type MarketTuple = readonly [string, bigint, number, `0x${string}`, bigint, bigint];

function MarketDetails({ market, now }: { market: MarketTuple; now: number }) {
  const [question, tradingDeadline, state, creator, yesQuantity, noQuantity] = market;
  const prices = lmsrPrices(yesQuantity, noQuantity);
  const tradable = isTradable(state, tradingDeadline, now);
  const stateLabel = MARKET_STATES[state] ?? `UNKNOWN (${state})`;

  return (
    <div className="mt-3 flex flex-col gap-3">
      <h2 className="text-lg font-semibold text-neutral-100">{question}</h2>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded bg-neutral-800 px-2 py-0.5 font-mono text-amber-300">{stateLabel}</span>
        {tradable ? (
          <span className="rounded bg-emerald-950 px-2 py-0.5 text-emerald-300">Trading open</span>
        ) : (
          <span className="rounded bg-red-950 px-2 py-0.5 text-red-300">Trading closed</span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <PriceTile label="YES" probability={prices.yes} shares={yesQuantity} accent="text-emerald-300" />
        <PriceTile label="NO" probability={prices.no} shares={noQuantity} accent="text-rose-300" />
      </div>

      <p className="text-sm text-neutral-400">
        Trading deadline: {new Date(Number(tradingDeadline) * 1000).toLocaleString()}
      </p>
      <p className="text-sm text-neutral-400">
        Creator: <span className="font-mono">{shortenAddress(creator)}</span>
      </p>
      {EXPLORER_URL && (
        <a
          href={`${EXPLORER_URL}/address/${PREDICTION_MARKET_ADDRESS}`}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-amber-300 underline underline-offset-2"
        >
          View contract on Etherscan
        </a>
      )}
    </div>
  );
}

function PriceTile({
  label,
  probability,
  shares,
  accent,
}: {
  label: string;
  probability: number;
  shares: bigint;
  accent: string;
}) {
  return (
    <div className="rounded-md border border-neutral-800 bg-neutral-950 p-3">
      <p className={`text-xs font-semibold ${accent}`}>{label}</p>
      <p className="mt-1 font-mono text-xl text-neutral-100">{formatPercent(probability)}</p>
      <p className="text-xs text-neutral-500">≈ {probability.toFixed(2)} ACON / share</p>
      <p className="mt-1 text-xs text-neutral-500">{formatTokenAmount(shares)} shares outstanding</p>
    </div>
  );
}
