import { DEMO_MARKET_ID, PREDICTION_MARKET_ADDRESS } from "./config";
import { formatPercent, formatTokenAmount } from "./format";
import { isTradable, lmsrPrices } from "./lmsr";
import { formatCountdown } from "./marketTime";
import { MARKET_STATES } from "./predictionMarket";
import { marketHref } from "./router";
import { SplitBar, Tag } from "./ui";
import { useMarkets, type Market } from "./useMarkets";
import { useNowSeconds } from "./useNow";

export function MarketsPage() {
  const { markets, isLoading, error } = useMarkets();
  const now = useNowSeconds();
  // Open markets first, newest first within each group; the configured
  // featured market leads.
  const sorted = [...(markets ?? [])].sort((a, b) => {
    if (a.id === DEMO_MARKET_ID) return -1;
    if (b.id === DEMO_MARKET_ID) return 1;
    const open = Number(isTradable(b.state, b.tradingDeadline, now)) - Number(isTradable(a.state, a.tradingDeadline, now));
    return open !== 0 ? open : Number(b.id - a.id);
  });
  const openCount = sorted.filter((m) => isTradable(m.state, m.tradingDeadline, now)).length;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-bronze/50 pb-5">
        <div className="flex flex-col items-start gap-2">
          <Tag>Markets</Tag>
          <h1 className="font-display text-3xl font-bold uppercase tracking-wide text-paper sm:text-4xl">Pick a side</h1>
          <p className="max-w-xl text-sand">
            Trade YES or NO shares on esports matches with test ACON. Prices move with every trade.
          </p>
        </div>
        {markets && (
          <div className="flex gap-6 font-mono">
            <Counter label="Open" value={openCount} accent="text-gold" />
            <Counter label="Total" value={sorted.length} accent="text-paper" />
          </div>
        )}
      </div>

      {!PREDICTION_MARKET_ADDRESS && <p className="text-signal">VITE_PREDICTION_MARKET_ADDRESS is not set (see frontend/.env.example).</p>}
      {isLoading && <p className="text-sand">Loading markets from the chain…</p>}
      {error && <p className="text-signal">Could not read markets: {error.message.split("\n")[0]}</p>}
      {markets && markets.length === 0 && (
        <p className="text-sand">
          No markets yet. Browse <a href="#/fixtures" className="link">fixtures</a> to see upcoming matches.
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {sorted.map((m) => (
          <MarketTile key={m.id.toString()} market={m} now={now} featured={m.id === DEMO_MARKET_ID} />
        ))}
      </div>
    </div>
  );
}

function Counter({ label, value, accent }: { label: string; value: number; accent: string }) {
  return (
    <div className="flex flex-col items-end">
      <span className={`num text-3xl font-medium ${accent}`}>{String(value).padStart(2, "0")}</span>
      <span className="label">{label}</span>
    </div>
  );
}

function MarketTile({ market, now, featured }: { market: Market; now: number; featured: boolean }) {
  const prices = lmsrPrices(market.yesQuantity, market.noQuantity);
  const open = isTradable(market.state, market.tradingDeadline, now);
  const volume = market.yesQuantity + market.noQuantity;

  return (
    <a
      href={marketHref(market.id)}
      className="hud group flex flex-col gap-4 border-l-2 border-bronze bg-ink-700 p-5 transition-colors hover:border-gold hover:bg-ink-600"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] text-dust">
          MKT-{market.id.toString().padStart(3, "0")}
          {featured && <span className="ml-2 text-gold">★ FEATURED</span>}
        </span>
        {open ? (
          <span className="flex items-center gap-1.5 font-display text-[11px] font-bold uppercase tracking-wider text-signal">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-signal" /> Live
          </span>
        ) : (
          <span className="font-display text-[11px] font-bold uppercase tracking-wider text-dust">
            {MARKET_STATES[market.state] === "OPEN" ? "Closed" : MARKET_STATES[market.state] ?? "Unknown"}
          </span>
        )}
      </div>

      <h3 className="font-display text-lg font-semibold leading-snug text-paper group-hover:text-gold">{market.question}</h3>

      <div className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between font-mono">
          <span>
            <span className="font-display text-xs font-bold tracking-wider text-gold">YES </span>
            <span className="num text-2xl text-paper">{formatPercent(prices.yes)}</span>
          </span>
          <span>
            <span className="num text-2xl text-paper">{formatPercent(prices.no)}</span>
            <span className="font-display text-xs font-bold tracking-wider text-signal-soft"> NO</span>
          </span>
        </div>
        <SplitBar yes={prices.yes} />
      </div>

      <div className="flex justify-between border-t border-bronze/40 pt-3 font-mono text-xs text-sand">
        <span>
          <span className="text-dust">SHARES </span>
          {formatTokenAmount(volume, 18, 0)}
        </span>
        <span>
          <span className="text-dust">{open ? "CLOSES IN " : ""}</span>
          {formatCountdown(market.tradingDeadline, now)}
        </span>
      </div>
    </a>
  );
}
