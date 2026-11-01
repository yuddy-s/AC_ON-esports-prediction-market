import { describe, expect, it } from "vitest";
import { deadlineProblem, fromLocalInput, maxDeadline, toLocalInput } from "./CreateMarket";

const START = 2_000_000_000n;

describe("create-market deadline", () => {
  it("allows at most the scheduled start minus 15 minutes", () => {
    expect(maxDeadline(START)).toBe(START - 900n);
    expect(deadlineProblem(START - 900n, 1_000, START)).toBeNull();
    expect(deadlineProblem(START - 899n, 1_000, START)).toMatch(/15 minutes before/);
  });

  it("must be strictly in the future by the chain clock", () => {
    expect(deadlineProblem(1_000n, 1_000, START)).toMatch(/future/);
    expect(deadlineProblem(1_001n, 1_000.5, START)).toBeNull();
  });

  it("requires a value", () => {
    expect(deadlineProblem(undefined, 0, START)).toMatch(/Pick/);
  });

  it("round-trips the datetime-local input to the minute", () => {
    const at = 1_800_000_000n; // a whole minute
    expect(fromLocalInput(toLocalInput(at))).toBe(at);
    expect(fromLocalInput("not a date")).toBeUndefined();
  });
});
