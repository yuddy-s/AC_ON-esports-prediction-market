import { useState } from "react";
import { useAccount, useReadContract, useReadContracts } from "wagmi";
import {
  ACON_TOKEN_ADDRESS,
  CHAIN,
  DEMO_MARKET_ID,
  EXPLORER_URL,
  PREDICTION_MARKET_ADDRESS,
} from "./config";
import { describeError } from "./errors";
import { formatTokenAmount } from "./format";
import { isTradable } from "./lmsr";
import { aconTokenAbi, OUTCOME, predictionMarketAbi, type Outcome } from "./predictionMarket";
import { computeMaxCost, parseBaseUnits, parseShares, parseSlippagePercent } from "./tradeMath";
import { useNowSeconds } from "./useNow";
import { isWrongNetwork } from "./walletSupport";
import { isBusy, isFailure, statusMessage, stepIndex, TRADE_STEPS, type TradeStatus } from "./tradeStatus";
import { useTradeFlow } from "./useTradeFlow";

export function TradePanel() {
  const { address, isConnected, chainId: walletChainId } = useAccount();
  const now = useNowSeconds();
  const [outcome, setOutcome] = useState<Outcome>(OUTCOME.YES);
  const [sharesInput, setSharesInput] = useState("10");
  const [slippageInput, setSlippageInput] = useState("1");
  const { status, buy, reset } = useTradeFlow();

  const market = PREDICTION_MARKET_ADDRESS;
  const token = ACON_TOKEN_ADDRESS;
  const configured = market !== undefined && token !== undefined;

  const marketRead = useReadContract({
    address: market,
    abi: predictionMarketAbi,
    functionName: "getMarket",
    args: [DEMO_MARKET_ID],
    chainId: CHAIN.id,
    query: { enabled: configured, refetchInterval: 10_000 },
  });
  const tradable = marketRead.data ? isTradable(marketRead.data[2], marketRead.data[1], now) : false;

  const shares = parseShares(sharesInput);
  const slippageBps = parseSlippagePercent(slippageInput);

  // Live on-chain quote: the same LMSR path the contract charges in buy().
  const quoteRead = useReadContract({
    address: market,
    abi: predictionMarketAbi,
    functionName: "quoteBuy",
    args: [DEMO_MARKET_ID, outcome, shares.ok ? shares.value : 0n],
    chainId: CHAIN.id,
    query: { enabled: configured && tradable && shares.ok, refetchInterval: 5_000 },
  });
  const quote = shares.ok ? quoteRead.data : undefined;
  const maxCost = quote !== undefined && slippageBps !== undefined ? computeMaxCost(quote, slippageBps) : undefined;

  const wallet = useReadContracts({
    contracts: [
      { address: token, abi: aconTokenAbi, functionName: "balanceOf", args: [address!], chainId: CHAIN.id },
      { address: token, abi: aconTokenAbi, functionName: "allowance", args: [address!, market!], chainId: CHAIN.id },
      { address: market, abi: predictionMarketAbi, functionName: "balanceOf", args: [DEMO_MARKET_ID, address!, OUTCOME.YES], chainId: CHAIN.id },
      { address: market, abi: predictionMarketAbi, functionName: "balanceOf", args: [DEMO_MARKET_ID, address!, OUTCOME.NO], chainId: CHAIN.id },
    ],
    allowFailure: false,
    query: { enabled: configured && isConnected && address !== undefined },
  });
  const [aconBalance, allowance, yesShares, noShares] = wallet.data ?? [];

  if (!isConnected || !address || !configured) return null;

  const busy = isBusy(status);
  const notEnoughAcon = quote !== undefined && aconBalance !== undefined && aconBalance < quote;
  const needsApproval = maxCost !== undefined && allowance !== undefined && allowance < maxCost;
  const wrongNetwork = isWrongNetwork(walletChainId, CHAIN.id);
  const canBuy =
    tradable && shares.ok && maxCost !== undefined && !notEnoughAcon && !busy && aconBalance !== undefined && !wrongNetwork;

  const onBuy = () => {
    if (!canBuy || !shares.ok || maxCost === undefined) return;
    void buy({
      account: address,
      market,
      token,
      marketId: DEMO_MARKET_ID,
      outcome,
      shares: shares.value,
      maxCost,
      needsApproval,
    });
  };

  return (
    <section className="flex flex-col gap-4 rounded-lg border border-neutral-700 bg-neutral-900 p-5">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-400">Buy shares</h2>

      <div className="grid grid-cols-2 gap-2">
        {([["YES", OUTCOME.YES], ["NO", OUTCOME.NO]] as const).map(([label, value]) => (
          <button
            key={label}
            onClick={() => setOutcome(value)}
            disabled={busy}
            className={`rounded-lg border px-4 py-2 font-semibold ${
              outcome === value
                ? value === OUTCOME.YES
                  ? "border-emerald-400 bg-emerald-950 text-emerald-300"
                  : "border-rose-400 bg-rose-950 text-rose-300"
                : "border-neutral-700 text-neutral-400 hover:bg-neutral-800"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1 text-xs text-neutral-400">
          Shares (max 100)
          <input
            value={sharesInput}
            onChange={(e) => setSharesInput(e.target.value)}
            disabled={busy}
            inputMode="decimal"
            className="rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 font-mono text-base text-neutral-100"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-neutral-400">
          Max slippage (%)
          <input
            value={slippageInput}
            onChange={(e) => setSlippageInput(e.target.value)}
            disabled={busy}
            inputMode="decimal"
            className="rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 font-mono text-base text-neutral-100"
          />
        </label>
      </div>

      <div className="rounded-md bg-neutral-950 p-3 text-sm">
        {!tradable && <p className="text-red-400">Trading is closed for this market.</p>}
        {tradable && !shares.ok && <p className="text-red-400">{shares.error}</p>}
        {tradable && shares.ok && slippageBps === undefined && (
          <p className="text-red-400">Slippage must be between 0 and 50%.</p>
        )}
        {tradable && shares.ok && quoteRead.error && (
          <p className="text-red-400">Cannot quote: {describeError(quoteRead.error)}</p>
        )}
        {tradable && shares.ok && quote !== undefined && (
          <div className="flex flex-col gap-1 font-mono">
            <Row label="Quoted cost" value={`${formatTokenAmount(quote, 18, 4)} ACON`} />
            {maxCost !== undefined && <Row label="You pay at most" value={`${formatTokenAmount(maxCost, 18, 4)} ACON`} />}
            {aconBalance !== undefined && <Row label="Your ACON" value={formatTokenAmount(aconBalance)} />}
          </div>
        )}
        {notEnoughAcon && <p className="mt-2 text-red-400">Not enough ACON for this trade. Claim from the faucet or buy fewer shares.</p>}
      </div>

      <button
        onClick={onBuy}
        disabled={!canBuy}
        className="rounded-lg bg-amber-400 px-5 py-2.5 font-semibold text-neutral-900 hover:bg-amber-300 disabled:opacity-40"
      >
        {needsApproval ? "Approve ACON, then buy" : "Buy"} {outcome === OUTCOME.YES ? "YES" : "NO"}
      </button>
      {needsApproval && !busy && (
        <p className="-mt-2 text-xs text-neutral-500">
          Two wallet steps: first allow the market to spend up to the max cost in ACON, then the buy itself.
        </p>
      )}

      <TradeStatusView status={status} onReset={reset} />

      <div className="border-t border-neutral-800 pt-3 text-sm text-neutral-400">
        Your position:{" "}
        <span className="font-mono text-emerald-300">{yesShares !== undefined ? formatTokenAmount(yesShares) : "…"} YES</span>
        {" · "}
        <span className="font-mono text-rose-300">{noShares !== undefined ? formatTokenAmount(noShares) : "…"} NO</span>
      </div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <p className="flex justify-between gap-4">
      <span className="font-sans text-neutral-400">{label}</span>
      <span className="text-neutral-100">{value}</span>
    </p>
  );
}

function TxLink({ hash }: { hash: string }) {
  const short = `${hash.slice(0, 10)}…${hash.slice(-6)}`;
  return EXPLORER_URL ? (
    <a href={`${EXPLORER_URL}/tx/${hash}`} target="_blank" rel="noreferrer" className="font-mono underline underline-offset-2">
      {short}
    </a>
  ) : (
    <span className="font-mono">{short}</span>
  );
}

function TradeStatusView({ status, onReset }: { status: TradeStatus; onReset: () => void }) {
  if (status.kind === "idle") return null;
  const current = stepIndex(status);
  const failed = isFailure(status);

  return (
    <div className="flex flex-col gap-3 rounded-md border border-neutral-800 bg-neutral-950 p-3 text-sm">
      {current >= 0 && (
        <ol className="grid grid-cols-4 gap-1 text-center text-xs">
          {TRADE_STEPS.map((step, i) => {
            const done = i < current || (i === current && (status.kind === "indexed" || (status.kind === "mined" && i === 2)));
            const active = i === current && !done;
            const bad = status.kind === "reverted" && i === 2;
            return (
              <li
                key={step}
                className={`rounded px-1 py-1 ${
                  bad
                    ? "bg-red-950 text-red-300"
                    : done
                      ? "bg-emerald-950 text-emerald-300"
                      : active
                        ? "bg-amber-950 text-amber-300"
                        : "bg-neutral-900 text-neutral-600"
                }`}
              >
                {bad ? "Reverted" : step}
              </li>
            );
          })}
        </ol>
      )}

      <p className={failed ? "text-red-400" : "text-neutral-300"}>{statusMessage(status)}</p>
      {"hash" in status && (
        <p className="text-xs text-neutral-500">
          Transaction: <TxLink hash={status.hash} />
        </p>
      )}
      {status.kind === "indexed" && (
        <p className="text-xs text-neutral-500">
          Indexed trade: {formatTokenAmount(parseBaseUnits(status.trade.shares))} shares for{" "}
          {formatTokenAmount(parseBaseUnits(status.trade.cost), 18, 4)} ACON (block {status.trade.block_number}).
        </p>
      )}

      {!isBusy(status) && (
        <button onClick={onReset} className="self-start text-xs text-amber-300 underline underline-offset-2">
          {failed ? "Dismiss" : "New trade"}
        </button>
      )}
    </div>
  );
}
