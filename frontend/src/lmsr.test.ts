import { describe, expect, it } from "vitest";
import { isTradable, lmsrPrices } from "./lmsr";

const ONE = 10n ** 18n;

describe("lmsrPrices", () => {
  it("starts a new market at 50/50", () => {
    expect(lmsrPrices(0n, 0n)).toEqual({ yes: 0.5, no: 0.5 });
  });

  it("YES and NO always sum to 1", () => {
    for (const [yes, no] of [[10n, 0n], [0n, 37n], [2000n, 0n], [123n, 456n]]) {
      const prices = lmsrPrices(yes * ONE, no * ONE);
      expect(prices.yes + prices.no).toBeCloseTo(1, 12);
    }
  });

  it("matches the LMSR formula with b = 50", () => {
    // 10 YES outstanding: 1 / (1 + e^(-10/50)) ≈ 0.5498 (the 55% shown in the demo)
    expect(lmsrPrices(10n * ONE, 0n).yes).toBeCloseTo(1 / (1 + Math.exp(-0.2)), 12);
    // 10 YES, 5 NO: 1 / (1 + e^(-5/50)) ≈ 0.525
    expect(lmsrPrices(10n * ONE, 5n * ONE).yes).toBeCloseTo(0.52498, 4);
  });

  it("buying an outcome raises its price", () => {
    const before = lmsrPrices(10n * ONE, 10n * ONE);
    const after = lmsrPrices(20n * ONE, 10n * ONE);
    expect(after.yes).toBeGreaterThan(before.yes);
    expect(after.no).toBeLessThan(before.no);
  });

  it("stays a valid probability at the 2,000-share quantity limit", () => {
    // e^-40 is below float precision next to 1, so YES displays as 100%.
    for (const prices of [lmsrPrices(2000n * ONE, 0n), lmsrPrices(0n, 2000n * ONE)]) {
      for (const p of [prices.yes, prices.no]) {
        expect(Number.isFinite(p)).toBe(true);
        expect(p).toBeGreaterThanOrEqual(0);
        expect(p).toBeLessThanOrEqual(1);
      }
    }
    expect(lmsrPrices(2000n * ONE, 0n).yes).toBeGreaterThan(0.999999);
  });
});

describe("isTradable", () => {
  const OPEN = 1;
  const deadline = 1_000n;

  it("is tradable when OPEN and before the deadline", () => {
    expect(isTradable(OPEN, deadline, 999)).toBe(true);
    expect(isTradable(OPEN, deadline, 999.9)).toBe(true);
  });

  it("closes exactly at the deadline (contract reverts TradingClosed)", () => {
    expect(isTradable(OPEN, deadline, 1000)).toBe(false);
    expect(isTradable(OPEN, deadline, 5000)).toBe(false);
  });

  it("is never tradable in a non-OPEN state", () => {
    for (const state of [0, 2, 3, 4, 5, 6]) {
      expect(isTradable(state, deadline, 0), `state ${state}`).toBe(false);
    }
  });
});
