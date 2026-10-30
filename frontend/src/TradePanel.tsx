import { useState, type ReactNode } from "react";
import { useAccount, useReadContract, useReadContracts } from "wagmi";
import { ACON_TOKEN_ADDRESS, CHAIN, EXPLORER_URL, PREDICTION_MARKET_ADDRESS } from "./config";
import { describeError } from "./errors";
import { formatTokenAmount } from "./format";
import { isTradable } from "./lmsr";
import { aconTokenAbi, OUTCOME, predictionMarketAbi, type Outcome } from "./predictionMarket";
import { computeMaxCost, parseBaseUnits, parseShares, parseSlippagePercent } from "./tradeMath";
import { useNowSeconds } from "./useNow";
import { isWrongNetwork } from "./walletSupport";
import { isBusy, isFailure, statusMessage, stepIndex, TRADE_STEPS, type TradeStatus } from "./tradeStatus";
import { useTradeFlow } from "./useTradeFlow";
import { Tag } from "./ui";

export function TradePanel({ marketId }: { marketId: bigint }) {
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
    args: [marketId],
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
    args: [marketId, outcome, shares.ok ? shares.value : 0n],
    chainId: CHAIN.id,
    query: { enabled: configured && tradable && shares.ok, refetchInterval: 5_000 },
  });
  const quote = shares.ok ? quoteRead.data : undefined;
  const maxCost = quote !== undefined && slippageBps !== undefined ? computeMaxCost(quote, slippageBps) : undefined;

  const wallet = useReadContracts({
    contracts: [
      { address: token, abi: aconTokenAbi, functionName: "balanceOf", args: [address!], chainId: CHAIN.id },
      { address: token, abi: aconTokenAbi, functionName: "allowance", args: [address!, market!], chainId: CHAIN.id },
      { address: market, abi: predictionMarketAbi, functionName: "balanceOf", args: [marketId, address!, OUTCOME.YES], chainId: CHAIN.id },
      { address: market, abi: predictionMarketAbi, functionName: "balanceOf", args: [marketId, address!, OUTCOME.NO], chainId: CHAIN.id },
    ],
    allowFailure: false,
    query: { enabled: configured && isConnected && address !== undefined },
  });
  const [aconBalance, allowance, yesShares, noShares] = wallet.data ?? [];

  if (!configured) return null;
  if (!isConnected || !address) {
    return (
      <Shell>
        <p className="text-sand">Connect a wallet (top right) to trade this market.</p>
      </Shell>
    );
  }

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
      marketId,
      outcome,
      shares: shares.value,
      maxCost,
      needsApproval,
    });
  };

  return (
    <Shell>
      <div className="grid grid-cols-2">
        {([["YES", OUTCOME.YES], ["NO", OUTCOME.NO]] as const).map(([label, value]) => {
          const selected = outcome === value;
          const color =
            value === OUTCOME.YES
              ? selected
                ? "bg-gold text-ink-900"
                : "text-gold hover:bg-gold/10"
              : selected
                ? "bg-signal-soft text-paper"
                : "text-signal-soft hover:bg-signal/10";
          return (
            <button
              key={label}
              onClick={() => setOutcome(value)}
              disabled={busy}
              className={`border border-bronze py-2.5 font-display text-base font-bold tracking-[0.2em] ${color}`}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1.5">
          <span className="label">Shares · max 100</span>
          <input value={sharesInput} onChange={(e) => setSharesInput(e.target.value)} disabled={busy} inputMode="decimal" className="field num" />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="label">Max slippage %</span>
          <input value={slippageInput} onChange={(e) => setSlippageInput(e.target.value)} disabled={busy} inputMode="decimal" className="field num" />
        </label>
      </div>

      <div className="border border-bronze/50 bg-ink-900 p-3 text-sm">
        {!tradable && <p className="text-signal">Trading is closed for this market.</p>}
        {tradable && !shares.ok && <p className="text-signal">{shares.error}</p>}
        {tradable && shares.ok && slippageBps === undefined && <p className="text-signal">Slippage must be between 0 and 50%.</p>}
        {tradable && shares.ok && quoteRead.error && <p className="text-signal">Cannot quote: {describeError(quoteRead.error)}</p>}
        {tradable && shares.ok && quote !== undefined && (
          <div className="flex flex-col gap-1.5 font-mono">
            <Row label="Quoted cost" value={`${formatTokenAmount(quote, 18, 4)} ACON`} strong />
            {maxCost !== undefined && <Row label="You pay at most" value={`${formatTokenAmount(maxCost, 18, 4)} ACON`} />}
            {aconBalance !== undefined && <Row label="Your ACON" value={formatTokenAmount(aconBalance)} />}
          </div>
        )}
        {notEnoughAcon && <p className="mt-2 text-signal">Not enough ACON for this trade. Claim from the faucet or buy fewer shares.</p>}
      </div>

      <button onClick={onBuy} disabled={!canBuy} className="btn-gold w-full py-3 text-base">
        {needsApproval ? "Approve ACON, then buy" : "Buy"} {outcome === OUTCOME.YES ? "YES" : "NO"}
      </button>
      {needsApproval && !busy && (
        <p className="-mt-2 text-xs text-dust">
          Two wallet steps: first allow the market to spend up to the max cost in ACON, then the buy itself.
        </p>
      )}

      <TradeStatusView status={status} onReset={reset} />

      <div className="grid grid-cols-2 border-t border-bronze/40 pt-3">
        <div>
          <p className="label">Your YES</p>
          <p className="num font-mono text-lg text-gold">{yesShares !== undefined ? formatTokenAmount(yesShares) : "…"}</p>
        </div>
        <div className="text-right">
          <p className="label">Your NO</p>
          <p className="num font-mono text-lg text-signal-soft">{noShares !== undefined ? formatTokenAmount(noShares) : "…"}</p>
        </div>
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <section className="hud flex flex-col gap-4 border-t-2 border-gold bg-ink-600 p-5">
      <div className="flex items-center justify-between">
        <Tag tone="gold">Trade</Tag>
        <span className="font-mono text-[11px] text-dust">BUY SHARES</span>
      </div>
      {children}
    </section>
  );
}

function Row({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <p className="flex justify-between gap-4">
      <span className="font-sans text-sand">{label}</span>
      <span className={`num ${strong ? "text-gold" : "text-paper"}`}>{value}</span>
    </p>
  );
}

function TxLink({ hash }: { hash: string }) {
  const short = `${hash.slice(0, 10)}…${hash.slice(-6)}`;
  return EXPLORER_URL ? (
    <a href={`${EXPLORER_URL}/tx/${hash}`} target="_blank" rel="noreferrer" className="link font-mono">
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
    <div className="flex flex-col gap-3 border border-bronze/50 bg-ink-900 p-3 text-sm">
      {current >= 0 && (
        <ol className="grid grid-cols-4 gap-1 text-center">
          {TRADE_STEPS.map((step, i) => {
            const done = i < current || (i === current && (status.kind === "indexed" || (status.kind === "mined" && i === 2)));
            const active = i === current && !done;
            const bad = status.kind === "reverted" && i === 2;
            return (
              <li
                key={step}
                className={`border-b-2 py-1 font-display text-[10px] font-semibold uppercase tracking-wider ${
                  bad
                    ? "border-signal text-signal"
                    : done
                      ? "border-win text-win"
                      : active
                        ? "animate-pulse border-gold text-gold"
                        : "border-ink-500 text-dust"
                }`}
              >
                {bad ? "Reverted" : step}
              </li>
            );
          })}
        </ol>
      )}

      <p className={failed ? "text-signal" : "text-cream"}>{statusMessage(status)}</p>
      {"hash" in status && (
        <p className="text-xs text-dust">
          Transaction: <TxLink hash={status.hash} />
        </p>
      )}
      {status.kind === "indexed" && (
        <p className="text-xs text-dust">
          Indexed trade: {formatTokenAmount(parseBaseUnits(status.trade.shares))} shares for{" "}
          {formatTokenAmount(parseBaseUnits(status.trade.cost), 18, 4)} ACON (block {status.trade.block_number}).
        </p>
      )}

      {!isBusy(status) && (
        <button onClick={onReset} className="link self-start text-xs">
          {failed ? "Dismiss" : "New trade"}
        </button>
      )}
    </div>
  );
}
