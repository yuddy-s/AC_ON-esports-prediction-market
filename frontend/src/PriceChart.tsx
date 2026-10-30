import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { API_URL, CHAIN, PREDICTION_MARKET_ADDRESS } from "./config";
import { formatPercent, formatTokenAmount } from "./format";
import { fetchAllMarketTrades, fetchIndexerStatus } from "./indexerApi";
import { indexerDeploymentProblem } from "./indexerHealth";
import { nearestPoint, stepPath, toPriceHistory, type PricePoint } from "./priceHistory";
import { Panel, PanelTitle } from "./ui";

const HEIGHT = 220;
const PAD = { top: 12, right: 56, bottom: 24, left: 40 };
const GRID = [0, 0.25, 0.5, 0.75, 1];

// YES price after every indexed trade. Built from the indexer's projection,
// so it is hidden whenever the indexer can't be trusted for this deployment.
export function PriceChart({ marketId }: { marketId: bigint }) {
  const trades = useQuery({
    queryKey: ["price-history", marketId.toString()],
    queryFn: ({ signal }) => fetchAllMarketTrades(marketId, signal),
    enabled: API_URL !== "",
    refetchInterval: 10_000,
  });
  const status = useQuery({
    queryKey: ["indexer-status"],
    queryFn: ({ signal }) => fetchIndexerStatus(signal),
    enabled: API_URL !== "",
    refetchInterval: 3_000,
  });

  if (!API_URL) return null;
  const problem = status.data ? indexerDeploymentProblem(status.data, CHAIN.id, PREDICTION_MARKET_ADDRESS) : null;
  const trusted = status.data && !status.isError && !problem;
  const points = trusted && trades.data ? toPriceHistory(trades.data.trades) : null;

  return (
    <Panel>
      <PanelTitle
        tag="Chart"
        title="YES price"
        aside={<span className="font-mono text-[11px] text-dust">AFTER EACH INDEXED TRADE</span>}
      />
      <div className="mt-4">
        {(status.isLoading || trades.isLoading) && <p className="text-sm text-sand">Loading price history…</p>}
        {(status.isError || trades.isError) && <p className="text-sm text-signal">Indexer API unreachable. The chart needs indexed trades.</p>}
        {problem && <p className="text-sm text-signal">{problem} The chart is hidden.</p>}
        {points && points.length === 1 && <p className="text-sm text-sand">No trades yet. The price starts at 50%.</p>}
        {points && points.length > 1 && <Chart points={points} />}
        {trades.data && trades.data.trades.length < trades.data.total && (
          <p className="mt-2 text-xs text-dust">Showing the first {trades.data.trades.length} of {trades.data.total} trades.</p>
        )}
      </div>
    </Panel>
  );
}

function Chart({ points }: { points: PricePoint[] }) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  const [active, setActive] = useState<number | null>(null);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(240, entry.contentRect.width)));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const plotW = width - PAD.left - PAD.right;
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const last = points.length - 1;
  const x = (i: number) => PAD.left + (last === 0 ? 0 : (i / last) * plotW);
  const y = (p: number) => PAD.top + (1 - p) * plotH;
  const xy = points.map((p) => ({ x: x(p.index), y: y(p.yes) }));
  const line = stepPath(xy);
  const area = `${line}V${y(0)}H${x(0)}Z`;
  const end = points[last];
  const shown = active === null ? null : points[active];

  const onMove = (e: PointerEvent<SVGRectElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const frac = ((e.clientX - rect.left) / rect.width) * last;
    setActive(nearestPoint(points.length, frac));
  };
  const onKey = (e: KeyboardEvent<SVGSVGElement>) => {
    if (e.key === "ArrowRight") setActive((a) => Math.min(last, (a ?? -1) + 1));
    else if (e.key === "ArrowLeft") setActive((a) => Math.max(0, (a ?? last + 1) - 1));
    else return;
    e.preventDefault();
  };

  return (
    <div ref={box} className="relative">
      <svg
        width={width}
        height={HEIGHT}
        role="img"
        aria-label={`YES price over ${last} trades, now ${formatPercent(end.yes)}. Use the arrow keys to step through trades.`}
        tabIndex={0}
        onKeyDown={onKey}
        onBlur={() => setActive(null)}
        className="block outline-none focus-visible:ring-1 focus-visible:ring-gold"
      >
        {GRID.map((g) => (
          <g key={g}>
            <line
              x1={PAD.left}
              x2={PAD.left + plotW}
              y1={y(g)}
              y2={y(g)}
              stroke={g === 0.5 ? "#7F7462" : "#4B3A26"}
              strokeWidth={1}
              strokeDasharray={g === 0.5 ? "4 4" : undefined}
            />
            <text x={PAD.left - 8} y={y(g) + 3} textAnchor="end" className="fill-dust font-mono text-[10px]">
              {g * 100}%
            </text>
          </g>
        ))}
        <text x={PAD.left} y={HEIGHT - 6} className="fill-dust font-mono text-[10px]">
          OPEN
        </text>
        <text x={PAD.left + plotW} y={HEIGHT - 6} textAnchor="end" className="fill-dust font-mono text-[10px]">
          TRADE {last}
        </text>

        <path d={area} fill="#F5C842" fillOpacity={0.1} />
        <path d={line} fill="none" stroke="#F5C842" strokeWidth={2} strokeLinejoin="round" />
        <circle cx={x(last)} cy={y(end.yes)} r={4} fill="#F5C842" stroke="#2C2117" strokeWidth={2} />
        <text x={x(last) + 8} y={y(end.yes) + 4} className="fill-paper font-mono text-[12px] font-medium">
          {formatPercent(end.yes)}
        </text>

        {shown && (
          <g pointerEvents="none">
            <line x1={x(shown.index)} x2={x(shown.index)} y1={PAD.top} y2={PAD.top + plotH} stroke="#B7A98D" strokeWidth={1} />
            <circle cx={x(shown.index)} cy={y(shown.yes)} r={4} fill="#F5C842" stroke="#2C2117" strokeWidth={2} />
          </g>
        )}
        <rect
          x={PAD.left}
          y={PAD.top}
          width={plotW}
          height={plotH}
          fill="transparent"
          onPointerMove={onMove}
          onPointerLeave={() => setActive(null)}
        />
      </svg>

      {shown && <Tooltip point={shown} left={x(shown.index)} width={width} />}
    </div>
  );
}

function Tooltip({ point, left, width }: { point: PricePoint; left: number; width: number }) {
  const flip = left > width - 190;
  return (
    <div
      className="pointer-events-none absolute top-2 w-44 border border-bronze bg-ink-900 px-3 py-2 shadow-lg shadow-black/50"
      style={flip ? { right: width - left + 10 } : { left: left + 10 }}
      role="status"
    >
      <p className="num font-mono text-lg text-paper">{formatPercent(point.yes)}</p>
      <p className="text-xs text-sand">YES price</p>
      {point.trade ? (
        <p className="mt-1 border-t border-bronze/40 pt-1 text-xs text-sand">
          Trade {point.index}: {formatTokenAmount(point.trade.shares)}{" "}
          <span className={point.trade.side === "YES" ? "text-gold" : "text-signal-soft"}>{point.trade.side}</span> · block{" "}
          {point.trade.block}
        </p>
      ) : (
        <p className="mt-1 border-t border-bronze/40 pt-1 text-xs text-sand">Market opened</p>
      )}
    </div>
  );
}
