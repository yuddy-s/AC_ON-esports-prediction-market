import { zeroAddress } from "viem";
import { useAccount, useReadContract, useReadContracts } from "wagmi";
import { ACON_TOKEN_ADDRESS, CHAIN, PREDICTION_MARKET_ADDRESS } from "./config";
import { formatTokenAmount } from "./format";
import { isSettled, portfolioRows, portfolioTotals, portfolioView, type Holding, type PortfolioRow } from "./portfolio";
import { aconTokenAbi, OUTCOME, predictionMarketAbi, STATE_LABELS } from "./predictionMarket";
import { marketHref } from "./router";
import { Panel, PanelTitle, Tag } from "./ui";
import { actionMessage, isActionBusy, useContractAction } from "./useContractAction";
import { useMarkets, type Market, type MarketTeams } from "./useMarkets";
import { useChainNowSeconds } from "./useNow";
import { isWrongNetwork } from "./walletSupport";

const market = { address: PREDICTION_MARKET_ADDRESS, abi: predictionMarketAbi, chainId: CHAIN.id } as const;

// Positions are contract reads (balanceOf, claimableAmount, hasClaimed), not
// indexed data, so spendable and claimable amounts are authoritative.
export function PortfolioPage() {
  const { address } = useAccount();
  const now = useChainNowSeconds();
  const marketsQuery = useMarkets();
  const { markets, teams } = marketsQuery;
  const user = address ?? zeroAddress;
  const list = markets ?? [];

  const reads = useReadContracts({
    contracts: list.flatMap((m) => [
      { ...market, functionName: "balanceOf" as const, args: [m.id, user, OUTCOME.YES] as const },
      { ...market, functionName: "balanceOf" as const, args: [m.id, user, OUTCOME.NO] as const },
      { ...market, functionName: "claimableAmount" as const, args: [m.id, user] as const },
      { ...market, functionName: "hasClaimed" as const, args: [m.id, user] as const },
      { ...market, functionName: "withdrawableSurplus" as const, args: [m.id] as const },
    ]),
    allowFailure: false,
    query: { enabled: address !== undefined && list.length > 0, refetchInterval: 10_000 },
  });
  const acon = useReadContract({
    address: ACON_TOKEN_ADDRESS,
    abi: aconTokenAbi,
    functionName: "balanceOf",
    args: [user],
    chainId: CHAIN.id,
    query: { enabled: address !== undefined && ACON_TOKEN_ADDRESS !== undefined },
  });

  const values = reads.data as readonly (bigint | boolean)[] | undefined;
  const holdings: (Holding | undefined)[] = list.map((_, i) =>
    values
      ? { yes: values[i * 5] as bigint, no: values[i * 5 + 1] as bigint, claimable: values[i * 5 + 2] as bigint, claimed: values[i * 5 + 3] as boolean }
      : undefined,
  );
  const surplus = list.map((_, i) => (values ? (values[i * 5 + 4] as bigint) : 0n));
  const rows = portfolioRows(list, holdings, now);
  const totals = portfolioTotals(rows);
  const view = portfolioView({
    connected: address !== undefined,
    marketCount: markets?.length,
    marketsError: marketsQuery.error,
    holdingsLoaded: values !== undefined,
    holdingsError: reads.error,
    rowCount: rows.length,
  });
  const created = list
    .map((m, i) => ({ m, surplus: surplus[i] }))
    .filter(({ m }) => address !== undefined && m.creator.toLowerCase() === address.toLowerCase());

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-bronze/50 pb-5">
        <div className="flex flex-col items-start gap-2">
          <Tag>Portfolio</Tag>
          <h1 className="font-display text-3xl font-bold uppercase tracking-wide text-paper sm:text-4xl">Your positions</h1>
          <p className="max-w-xl text-sand">Shares and payouts read straight from the contract for the connected wallet.</p>
        </div>
        {address && (
          <div className="flex flex-wrap gap-6 font-mono">
            <Figure label="ACON" value={acon.data !== undefined ? formatTokenAmount(acon.data) : "…"} accent="text-paper" />
            <Figure label="Open value (est.)" value={formatTokenAmount(totals.openValue)} accent="text-gold" />
            <Figure label="Ready to claim" value={formatTokenAmount(totals.claimable)} accent="text-win" />
            <Figure label="Active markets" value={String(totals.markets).padStart(2, "0")} accent="text-paper" />
          </div>
        )}
      </div>

      {view.kind === "disconnected" && <p className="text-sand">Connect a wallet (top right) to see your positions.</p>}
      {view.kind === "loading" && <p className="text-sand">Reading your positions from the chain…</p>}
      {view.kind === "error" && (
        <div className="flex flex-col items-start gap-1.5">
          <p className="text-signal">Couldn't read your positions from the chain. Check the network and try again.</p>
          <p className="break-words font-mono text-[11px] text-dust">{view.message}</p>
          <button
            type="button"
            className="btn-ghost"
            onClick={() => {
              marketsQuery.refetch();
              void reads.refetch();
            }}
          >
            Retry
          </button>
        </div>
      )}
      {view.kind === "no-markets" && (
        <p className="text-sand">
          There are no markets on this deployment yet. Create one from a registered <a href="#/fixtures" className="link">fixture</a>.
        </p>
      )}
      {view.kind === "no-positions" && (
        <p className="text-sand">
          No positions yet. <a href="#/" className="link">Browse markets</a> to make your first trade.
        </p>
      )}

      {view.kind === "positions" && (
        <Panel className="overflow-x-auto">
          <PanelTitle tag="Positions" title={`${totals.markets} active · ${rows.length - totals.markets} claimed`} />
          <table className="mt-4 w-full min-w-[640px] text-left text-sm">
            <thead className="label">
              <tr>
                <th className="pb-2 font-semibold">Market</th>
                <th className="pb-2 font-semibold">Status</th>
                <th className="pb-2 text-right font-semibold">YES</th>
                <th className="pb-2 text-right font-semibold">NO</th>
                <th className="pb-2 text-right font-semibold">Value (ACON)</th>
                <th className="pb-2" />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <PositionRow key={r.market.id.toString()} row={r} teams={teams.get(r.market.fixtureKey)} />
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-dust">
            Estimates use the current display price and are not a quote; settled values are the exact amount the contract will pay.
          </p>
        </Panel>
      )}

      {created.length > 0 && (
        <Panel>
          <PanelTitle tag="Creator" title="Markets you created" />
          <ul className="mt-3 flex flex-col">
            {created.map(({ m, surplus: s }) => (
              <CreatedRow key={m.id.toString()} market={m} teams={teams.get(m.fixtureKey)} surplus={s} />
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}

function Figure({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="flex flex-col items-end">
      <span className={`num text-2xl font-medium ${accent}`}>{value}</span>
      <span className="label">{label}</span>
    </div>
  );
}

function MarketName({ market: m, teams }: { market: Market; teams?: MarketTeams }) {
  return (
    <a href={marketHref(m.id)} className="group block">
      {teams && (
        <span className="block font-display text-xs font-semibold uppercase tracking-wide">
          <span className="text-gold">{teams.teamA}</span> <span className="text-dust">vs</span>{" "}
          <span className="text-signal-soft">{teams.teamB}</span>
        </span>
      )}
      <span className="text-paper group-hover:text-gold">{m.question}</span>
    </a>
  );
}

function statusLabel(row: PortfolioRow): string {
  if (row.tradable) return "Live";
  if (row.valueKind === "claimed") return "Claimed";
  return STATE_LABELS[row.market.state] ?? "Unknown";
}

function PositionRow({ row, teams }: { row: PortfolioRow; teams?: MarketTeams }) {
  const { address, chainId } = useAccount();
  const { status, run, reset } = useContractAction();
  const busy = isActionBusy(status);
  const failed = ["error", "reverted", "rejected"].includes(status.kind);

  return (
    <>
      <tr className="border-t border-bronze/30 align-top">
        <td className="py-2.5 pr-3">
          <MarketName market={row.market} teams={teams} />
        </td>
        <td className="py-2.5 pr-3">
          <span className={`font-display text-xs font-bold uppercase tracking-wider ${row.tradable ? "text-signal" : row.canClaim ? "text-win" : "text-sand"}`}>
            {statusLabel(row)}
          </span>
        </td>
        <td className="num py-2.5 text-right font-mono text-gold">{formatTokenAmount(row.holding.yes)}</td>
        <td className="num py-2.5 text-right font-mono text-signal-soft">{formatTokenAmount(row.holding.no)}</td>
        <td className="num py-2.5 text-right font-mono text-paper">
          {row.valueKind === "claimed" ? "—" : formatTokenAmount(row.value, 18, 4)}
          <span className="block text-[10px] text-dust">{row.valueKind === "estimate" ? "estimate" : row.valueKind === "exact" ? "exact payout" : ""}</span>
        </td>
        <td className="py-2.5 pl-3 text-right">
          {row.canClaim && address ? (
            <button
              className="btn-gold whitespace-nowrap px-3 py-1.5 text-xs"
              disabled={busy || isWrongNetwork(chainId, CHAIN.id)}
              onClick={() => void run({ account: address, call: { functionName: "claimPayout", args: [row.market.id] } })}
            >
              {busy ? "Claiming…" : "Claim"}
            </button>
          ) : (
            <a href={marketHref(row.market.id)} className="btn-ghost inline-block whitespace-nowrap">
              {row.tradable ? "Trade" : "View"}
            </a>
          )}
        </td>
      </tr>
      {status.kind !== "idle" && (
        <tr>
          <td colSpan={6} className="pb-2 text-right text-xs">
            <span className={failed ? "text-signal" : "text-cream"}>{actionMessage(status, "claim")}</span>
            {!busy && (
              <button onClick={reset} className="link ml-2">
                Dismiss
              </button>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function CreatedRow({ market: m, teams, surplus }: { market: Market; teams?: MarketTeams; surplus: bigint }) {
  const { address, chainId } = useAccount();
  const { status, run } = useContractAction();
  const busy = isActionBusy(status);
  const settled = isSettled(m.state);

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 border-t border-bronze/30 py-2.5 text-sm">
      <MarketName market={m} teams={teams} />
      <span className="flex items-center gap-3">
        <span className="num font-mono text-xs text-sand">
          {settled ? `Surplus ${formatTokenAmount(surplus, 18, 4)} ACON` : `Collateral ${formatTokenAmount(m.collateralBalance, 18, 2)} ACON`}
        </span>
        {settled && surplus > 0n && address && (
          <button
            className="btn-ghost"
            disabled={busy || isWrongNetwork(chainId, CHAIN.id)}
            onClick={() => void run({ account: address, call: { functionName: "withdrawCreatorSurplus", args: [m.id] } })}
          >
            {busy ? "Withdrawing…" : "Withdraw"}
          </button>
        )}
        {status.kind === "done" && <span className="text-xs text-win">Withdrawn</span>}
        {["error", "reverted", "rejected"].includes(status.kind) && <span className="text-xs text-signal">{actionMessage(status, "withdrawal")}</span>}
      </span>
    </li>
  );
}
