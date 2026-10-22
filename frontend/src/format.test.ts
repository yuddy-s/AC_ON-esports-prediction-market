import { describe, expect, it } from "vitest";
import { formatPercent, formatTokenAmount, shortenAddress } from "./format";

describe("formatTokenAmount", () => {
  it("groups thousands and keeps two decimals by default", () => {
    expect(formatTokenAmount(965_342_640_972_002_734_529n)).toBe("965.34");
    expect(formatTokenAmount(1_234_567_891n * 10n ** 15n)).toBe("1,234,567.89");
  });

  it("truncates instead of rounding, so balances are never overstated", () => {
    expect(formatTokenAmount(999_999n * 10n ** 13n)).toBe("9.99");
  });

  it("drops trailing zeros and whole-number decimals", () => {
    expect(formatTokenAmount(1000n * 10n ** 18n)).toBe("1,000");
    expect(formatTokenAmount(15n * 10n ** 17n)).toBe("1.5");
    expect(formatTokenAmount(0n)).toBe("0");
  });

  it("supports other precisions and decimals", () => {
    expect(formatTokenAmount(5_249_584_441_082_326_050n, 18, 4)).toBe("5.2495");
    expect(formatTokenAmount(123_456n, 6)).toBe("0.12");
  });

  it("handles negative amounts", () => {
    expect(formatTokenAmount(-25n * 10n ** 17n)).toBe("-2.5");
  });
});

describe("shortenAddress", () => {
  it("keeps the prefix and last four characters", () => {
    expect(shortenAddress("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")).toBe("0xf39F...2266");
  });
});

describe("formatPercent", () => {
  it("shows one decimal place", () => {
    expect(formatPercent(0.5)).toBe("50.0%");
    expect(formatPercent(0.549834)).toBe("55.0%");
  });
});
