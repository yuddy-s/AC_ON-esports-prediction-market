import { describe, expect, it } from "vitest";
import { chainNow } from "./useNow";

describe("chainNow", () => {
  it("uses the block timestamp plus the time since it was read", () => {
    expect(chainNow(1_800_000_000n, 10_000, 13_500)).toBe(1_800_000_003.5);
  });

  it("follows a fast-forwarded local chain, not the browser clock", () => {
    const dayAhead = BigInt(Math.floor(Date.now() / 1000) + 86_400);
    expect(chainNow(dayAhead, Date.now(), Date.now())).toBeGreaterThan(Date.now() / 1000 + 86_000);
  });

  it("falls back to the browser clock before the first block is read", () => {
    expect(chainNow(undefined, 0, 5_000)).toBe(5);
  });
});
