import { EXPLORER_URL, PREDICTION_MARKET_ADDRESS } from "./config";
import { formatPercent, formatTokenAmount, shortenAddress } from "./format";
import { gameLabel } from "./fixtureStatus";
import { isTradable, lmsrPrices } from "./lmsr";
import { formatCountdown } from "./marketTime";
import { MARKET_STATES } from "./predictionMarket";
import { PriceChart } from "./PriceChart";
import { RecentTrades } from "./RecentTrades";
import { ResolutionPanel } from "./ResolutionPanel";
import { TradePanel } from "./TradePanel";
import { Panel, PanelTitle, SplitBar, Stat, Tag } from "./ui";
import { useMarket, type Market, type MarketTeams } from "./useMarkets";
import { useChainNowSeconds } from "./useNow";

export function MarketPage({ id }: { id: bigint }) {
  const { market, teams, isLoading, error } = useMarket(id);

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
      {market && <MarketBody market={market} teams={teams} />}
    </div>
  );
}

function MarketBody({ market, teams }: { market: Market; teams?: MarketTeams }) {
  const now = useChainNowSeconds();
  const prices = lmsrPrices(market.yesQuantity, market.noQuantity);
  const open = isTradable(market.state, market.tradingDeadline, now);
  const resolution = <ResolutionPanel marketData={market} teams={teams} />;

  return (
    <>
      <Scoreboard market={market} teams={teams} yes={prices.yes} no={prices.no} open={open} />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex flex-col gap-6">
          {!open && resolution}
          <PriceChart marketId={market.id} />
          {open && resolution}
          <Panel>
            <PanelTitle tag="Market" title="Details" />
            <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Stored state" value={MARKET_STATES[market.state] ?? `UNKNOWN (${market.state})`} sub={open ? "Trading open" : "Trading closed"} />
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
              <span>
                Collateral <span className="num font-mono text-paper">{formatTokenAmount(market.collateralBalance)} ACON</span>
              </span>
              {teams && (
                <span>
                  Match start <span className="text-paper">{new Date(Number(teams.scheduledStart) * 1000).toLocaleString()}</span>
                </span>
              )}
              {EXPLORER_URL && (
                <a href={`${EXPLORER_URL}/address/${PREDICTION_MARKET_ADDRESS}`} target="_blank" rel="noreferrer" className="link">
                  Contract on explorer
                </a>
              )}
            </div>
            <p className="mt-3 text-xs text-dust">
              Prices are the LMSR formula on outstanding shares (display only). What you pay or receive always comes from
              the contract's quote.
            </p>
          </Panel>
          <RecentTrades marketId={market.id} />
        </div>

        <div className="lg:sticky lg:top-24">
          <TradePanel marketId={market.id} teams={teams} />
        </div>
      </div>
    </>
  );
}

// Broadcast-style score bug: YES side (Team A) in green, NO side (Team B) in rose.
function Scoreboard({ market, teams, yes, no, open }: { market: Market; teams?: MarketTeams; yes: number; no: number; open: boolean }) {
  return (
    <div className="hud overflow-hidden bg-ink-900">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-bronze/50 px-5 py-2">
        <span className="font-mono text-[11px] uppercase text-dust">
          MKT-{market.id.toString().padStart(3, "0")}
          {teams && ` · ${gameLabel(teams.gameId)}`}
        </span>
        {open ? <Tag>Live</Tag> : <Tag tone="gold">Trading closed</Tag>}
      </div>
      <h1 className="px-5 pt-4 font-display text-2xl font-bold leading-tight text-paper sm:text-3xl">{market.question}</h1>
      <div className="grid grid-cols-[1fr_auto_1fr] items-stretch gap-0 px-5 pb-5 pt-4">
        <Side label="YES" team={teams?.teamA} price={yes} align="left" color="text-win" />
        <div className="flex items-center px-4 font-display text-sm font-bold text-dust">VS</div>
        <Side label="NO" team={teams?.teamB} price={no} align="right" color="text-signal-soft" />
      </div>
      <SplitBar yes={yes} height="h-1.5" />
    </div>
  );
}

function Side({ label, team, price, align, color }: { label: string; team?: string; price: number; align: "left" | "right"; color: string }) {
  return (
    <div className={`flex min-w-0 flex-col ${align === "right" ? "items-end text-right" : "items-start"}`}>
      <span className={`font-display text-sm font-bold tracking-[0.2em] ${color}`}>
        {label}
        {team && <span className="ml-2 tracking-normal text-paper">{team}</span>}
      </span>
      <span className="num font-mono text-4xl text-paper sm:text-5xl">{formatPercent(price)}</span>
      <span className="font-mono text-xs text-dust">≈ {price.toFixed(2)} ACON / share</span>
    </div>
  );
}
