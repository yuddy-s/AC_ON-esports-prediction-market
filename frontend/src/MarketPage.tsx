import { EXPLORER_URL, PREDICTION_MARKET_ADDRESS } from "./config";
import { formatPercent, formatTokenAmount, shortenAddress } from "./format";
import { isTradable, lmsrPrices } from "./lmsr";
import { formatCountdown } from "./marketTime";
import { MARKET_STATES } from "./predictionMarket";
import { PriceChart } from "./PriceChart";
import { RecentTrades } from "./RecentTrades";
import { TradePanel } from "./TradePanel";
import { Panel, PanelTitle, SplitBar, Stat, Tag } from "./ui";
import { useMarket, type Market } from "./useMarkets";
import { useNowSeconds } from "./useNow";

export function MarketPage({ id }: { id: bigint }) {
  const { market, isLoading, error } = useMarket(id);

  return (
    <div className="flex flex-col gap-6">
      <a href="#/" className="font-display text-xs font-semibold uppercase tracking-wider text-sand hover:text-gold">
        ← All markets
      </a>
      {isLoading && <p className="text-sand">Loading market…</p>}
      {error && (
        <p className="text-signal">
          Could not read market #{id.toString()}: {error.message.split("\n")[0]}
        </p>
      )}
      {market && <MarketBody market={market} />}
    </div>
  );
}

function MarketBody({ market }: { market: Market }) {
  const now = useNowSeconds();
  const prices = lmsrPrices(market.yesQuantity, market.noQuantity);
  const open = isTradable(market.state, market.tradingDeadline, now);
  const stateLabel = MARKET_STATES[market.state] ?? `UNKNOWN (${market.state})`;

  return (
    <>
      <Scoreboard market={market} yes={prices.yes} no={prices.no} open={open} />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex flex-col gap-6">
          <PriceChart marketId={market.id} />
          <Panel>
            <PanelTitle tag="Market" title="Details" />
            <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="State" value={stateLabel} sub={open ? "Trading open" : "Trading closed"} />
              <Stat
                label="Deadline"
                value={formatCountdown(market.tradingDeadline, now)}
                sub={new Date(Number(market.tradingDeadline) * 1000).toLocaleString()}
              />
              <Stat label="YES shares" value={formatTokenAmount(market.yesQuantity)} sub="outstanding" />
              <Stat label="NO shares" value={formatTokenAmount(market.noQuantity)} sub="outstanding" />
            </div>
            <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 border-t border-bronze/40 pt-3 text-sm text-sand">
              <span>
                Creator <span className="font-mono text-paper">{shortenAddress(market.creator)}</span>
              </span>
              {EXPLORER_URL && (
                <a href={`${EXPLORER_URL}/address/${PREDICTION_MARKET_ADDRESS}`} target="_blank" rel="noreferrer" className="link">
                  Contract on explorer
                </a>
              )}
            </div>
            <p className="mt-3 text-xs text-dust">
              Prices are the LMSR formula on outstanding shares (display only). What you pay always comes from the
              contract's quote.
            </p>
          </Panel>
          <RecentTrades marketId={market.id} />
        </div>

        <div className="lg:sticky lg:top-24">
          <TradePanel marketId={market.id} />
        </div>
      </div>
    </>
  );
}

// Broadcast-style score bug: YES side in gold, NO side in red.
function Scoreboard({ market, yes, no, open }: { market: Market; yes: number; no: number; open: boolean }) {
  return (
    <div className="hud overflow-hidden bg-ink-900">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-bronze/50 px-5 py-2">
        <span className="font-mono text-[11px] text-dust">MKT-{market.id.toString().padStart(3, "0")}</span>
        {open ? <Tag>Live</Tag> : <Tag tone="gold">Closed</Tag>}
      </div>
      <h1 className="px-5 pt-4 font-display text-2xl font-bold leading-tight text-paper sm:text-3xl">{market.question}</h1>
      <div className="grid grid-cols-[1fr_auto_1fr] items-stretch gap-0 px-5 pb-5 pt-4">
        <Side label="YES" price={yes} align="left" color="text-gold" />
        <div className="flex items-center px-4 font-display text-sm font-bold text-dust">VS</div>
        <Side label="NO" price={no} align="right" color="text-signal-soft" />
      </div>
      <SplitBar yes={yes} height="h-1.5" />
    </div>
  );
}

function Side({ label, price, align, color }: { label: string; price: number; align: "left" | "right"; color: string }) {
  return (
    <div className={`flex flex-col ${align === "right" ? "items-end text-right" : "items-start"}`}>
      <span className={`font-display text-sm font-bold tracking-[0.2em] ${color}`}>{label}</span>
      <span className="num font-mono text-4xl text-paper sm:text-5xl">{formatPercent(price)}</span>
      <span className="font-mono text-xs text-dust">≈ {price.toFixed(2)} ACON / share</span>
    </div>
  );
}
