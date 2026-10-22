import { describe, expect, it } from "vitest";
import { computeMaxCost, parseBaseUnits, parseShares, parseSlippagePercent } from "./tradeMath";

const ONE = 10n ** 18n;

describe("parseShares", () => {
  it("converts decimal shares to 1e18 base units", () => {
    expect(parseShares("10")).toEqual({ ok: true, value: 10n * ONE });
    expect(parseShares("12.5")).toEqual({ ok: true, value: 125n * 10n ** 17n });
    expect(parseShares(" 0.000000000000000001 ")).toEqual({ ok: true, value: 1n });
  });

  it("accepts exactly the 100-share limit and rejects anything above it", () => {
    expect(parseShares("100")).toEqual({ ok: true, value: 100n * ONE });
    expect(parseShares("100.000000000000000001")).toEqual({ ok: false, error: "Max 100 shares per trade." });
    expect(parseShares("150")).toEqual({ ok: false, error: "Max 100 shares per trade." });
  });

  it("rejects empty, zero and non-numeric input", () => {
    expect(parseShares("")).toMatchObject({ ok: false, error: "Enter a number of shares." });
    expect(parseShares("0")).toMatchObject({ ok: false, error: "Shares must be greater than 0." });
    expect(parseShares("0.0")).toMatchObject({ ok: false });
    for (const bad of ["-5", "abc", "1e3", ".", "1.2.3"]) {
      expect(parseShares(bad).ok, bad).toBe(false);
    }
  });

  it("rejects more than 18 decimal places", () => {
    expect(parseShares("1.0000000000000000001")).toEqual({ ok: false, error: "Use at most 18 decimal places." });
  });
});

describe("computeMaxCost", () => {
  it("equals the quote with zero slippage", () => {
    expect(computeMaxCost(5_249_584_441_082_326_050n, 0)).toBe(5_249_584_441_082_326_050n);
  });

  it("adds the slippage percentage", () => {
    expect(computeMaxCost(100n * ONE, 100)).toBe(101n * ONE); // 1%
    expect(computeMaxCost(100n * ONE, 50)).toBe(1005n * 10n ** 17n); // 0.5%
  });

  it("rounds up so the guard is never below the quote plus slippage", () => {
    expect(computeMaxCost(1n, 100)).toBe(2n);
    expect(computeMaxCost(10_001n, 1)).toBe(10_003n);
  });

  it("rejects invalid slippage", () => {
    expect(() => computeMaxCost(ONE, -1)).toThrow();
    expect(() => computeMaxCost(ONE, 1.5)).toThrow();
  });
});

describe("parseSlippagePercent", () => {
  it("converts percent to basis points", () => {
    expect(parseSlippagePercent("1")).toBe(100);
    expect(parseSlippagePercent("0.5")).toBe(50);
    expect(parseSlippagePercent("0")).toBe(0);
  });

  it("rejects empty, negative, non-numeric and above-50% values", () => {
    for (const bad of ["", " ", "-1", "abc", "51"]) {
      expect(parseSlippagePercent(bad), bad).toBeUndefined();
    }
  });
});

describe("parseBaseUnits (backend Decimal strings)", () => {
  it("parses plain, decimal and exponent forms exactly", () => {
    expect(parseBaseUnits("5249584441082326050")).toBe(5_249_584_441_082_326_050n);
    expect(parseBaseUnits("10000000000000000000.0")).toBe(10n * ONE);
    expect(parseBaseUnits("1E+19")).toBe(10n * ONE);
    expect(parseBaseUnits("1.5e3")).toBe(1500n);
    expect(parseBaseUnits(0)).toBe(0n);
  });

  it("rejects fractional base units and junk", () => {
    expect(() => parseBaseUnits("1.5")).toThrow();
    expect(() => parseBaseUnits("-1")).toThrow();
    expect(() => parseBaseUnits("abc")).toThrow();
  });
});
