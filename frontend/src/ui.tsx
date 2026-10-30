import type { ReactNode } from "react";
import { formatPercent } from "./format";

// Shared building blocks for the broadcast look (palette from the slides).

export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`hud border-l-2 border-bronze bg-ink-700 p-5 ${className}`}>{children}</section>;
}

// Red label block, like the section tags on the milestone slides.
export function Tag({ children, tone = "red" }: { children: ReactNode; tone?: "red" | "gold" }) {
  const colors = tone === "red" ? "bg-signal-soft text-paper" : "bg-gold text-ink-900";
  return (
    <span className={`inline-block px-2 py-0.5 font-display text-[11px] font-bold uppercase tracking-[0.2em] ${colors}`}>
      {children}
    </span>
  );
}

export function PanelTitle({ tag, title, aside }: { tag?: string; title: string; aside?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-2">
      <div className="flex flex-col items-start gap-1.5">
        {tag && <Tag>{tag}</Tag>}
        <h2 className="font-display text-lg font-semibold uppercase tracking-wide text-paper">{title}</h2>
      </div>
      {aside}
    </div>
  );
}

// Red / gold / bronze dots from the slide deck.
export function Dots({ size = "h-2 w-2" }: { size?: string }) {
  return (
    <span className="inline-flex gap-1" aria-hidden>
      <span className={`${size} rounded-full bg-signal`} />
      <span className={`${size} rounded-full bg-gold`} />
      <span className={`${size} rounded-full bg-bronze-light`} />
    </span>
  );
}

// Tug-of-war bar: gold YES share against red NO share.
export function SplitBar({ yes, height = "h-2" }: { yes: number; height?: string }) {
  const pct = Math.min(100, Math.max(0, yes * 100));
  return (
    <div className={`flex ${height} w-full overflow-hidden bg-ink-900`} role="img" aria-label={`YES ${formatPercent(yes)}`}>
      <div className="bg-gold" style={{ width: `${pct}%` }} />
      <div className="w-0.5 bg-ink-900" />
      <div className="flex-1 bg-signal-soft" />
    </div>
  );
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="label">{label}</span>
      <span className="num font-mono text-paper">{value}</span>
      {sub && <span className="text-xs text-dust">{sub}</span>}
    </div>
  );
}
