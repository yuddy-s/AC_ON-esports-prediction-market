import type { ReactNode } from "react";
import type { Tone } from "./fixtureStatus";

const TONES: Record<Tone, string> = {
  neutral: "bg-neutral-800 text-neutral-300",
  good: "bg-emerald-950 text-emerald-300",
  warn: "bg-amber-950 text-amber-300",
  bad: "bg-red-950 text-red-300",
};

export function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`rounded px-2 py-0.5 text-xs ${TONES[tone]}`}>{children}</span>;
}
