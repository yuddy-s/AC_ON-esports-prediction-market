import type { ReactNode } from "react";
import type { Tone } from "./fixtureStatus";

const TONES: Record<Tone, string> = {
  neutral: "border-bronze text-sand",
  good: "border-win/60 text-win",
  warn: "border-gold/60 text-gold",
  bad: "border-signal/70 text-signal",
};

export function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center border px-1.5 py-0.5 font-display text-[10px] font-semibold uppercase tracking-[0.14em] ${TONES[tone]}`}>
      {children}
    </span>
  );
}
