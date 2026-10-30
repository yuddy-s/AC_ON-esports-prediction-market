import { describe, expect, it } from "vitest";
import { formatCountdown } from "./marketTime";

describe("formatCountdown", () => {
  const now = 1_800_000_000;

  it("shows the two largest units", () => {
    expect(formatCountdown(BigInt(now + 2 * 86_400 + 4 * 3_600 + 59), now)).toBe("2d 4h");
    expect(formatCountdown(BigInt(now + 3 * 3_600 + 12 * 60), now)).toBe("3h 12m");
    expect(formatCountdown(BigInt(now + 45 * 60 + 30), now)).toBe("45m");
  });

  it("counts the final seconds as under a minute", () => {
    expect(formatCountdown(BigInt(now + 20), now)).toBe("<1m");
  });

  it("is closed at and after the deadline", () => {
    expect(formatCountdown(BigInt(now), now)).toBe("Closed");
    expect(formatCountdown(BigInt(now - 1), now + 0.9)).toBe("Closed");
  });
});
