import { describe, expect, it } from "vitest";
import { ContractFunctionExecutionError, ContractFunctionRevertedError, encodeErrorResult, HttpRequestError } from "viem";
import { deadlineProblem, fixtureKey, fromLocalInput, maxDeadline, registrationRead, toLocalInput } from "./CreateMarket";
import { predictionMarketAbi } from "./predictionMarket";

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

describe("registrationRead (FixtureNotRegistered vs read failures)", () => {
  const key = `0x${"ab".repeat(32)}` as const;
  const notRegistered = () => {
    const data = encodeErrorResult({ abi: predictionMarketAbi, errorName: "FixtureNotRegistered", args: [key] });
    return new ContractFunctionExecutionError(new ContractFunctionRevertedError({ abi: predictionMarketAbi, data, functionName: "getFixture" }), {
      abi: predictionMarketAbi,
      functionName: "getFixture",
      args: [key],
    });
  };
  const rpcDown = () =>
    new ContractFunctionExecutionError(new HttpRequestError({ url: "http://127.0.0.1:8545", details: "fetch failed" }), {
      abi: predictionMarketAbi,
      functionName: "getFixture",
      args: [key],
    });
  const fixture = (registered: boolean) => ({
    data: { teamAName: "Cloud9", teamBName: "Evil Geniuses", scheduledStart: 2_000_000_000n },
    revisionHash: key,
    registered,
    hasMarket: false,
    marketId: 0n,
  });

  it("treats the contract's FixtureNotRegistered revert as not registered", () => {
    expect(registrationRead({ fixtureError: notRegistered(), data: undefined })).toEqual({ kind: "not-registered" });
  });

  it("reports an RPC or network failure as a retryable error, not as not registered", () => {
    const read = registrationRead({ fixtureError: rpcDown(), data: undefined });
    expect(read.kind).toBe("error");
  });

  it("is loading until a read answers", () => {
    expect(registrationRead({ fixtureError: null, data: undefined })).toEqual({ kind: "loading" });
  });

  it("returns the registered fixture", () => {
    expect(registrationRead({ fixtureError: null, data: fixture(true) })).toMatchObject({ kind: "registered" });
    expect(registrationRead({ fixtureError: null, data: fixture(false) })).toEqual({ kind: "not-registered" });
  });
});

describe("fixtureKey", () => {
  it("matches the contract's computeFixtureKey (value read from a local M4 deployment)", () => {
    expect(fixtureKey("acon-mock", "valorant", "demo-create")).toBe("0x02ebd7c19913192eba47ee6ad5d0ce316ed9ae36415a0faa6b3cf184e4a98bf0");
  });

  it("does not normalize the identity strings", () => {
    expect(fixtureKey("acon-mock", "Valorant", "demo-create")).not.toBe(fixtureKey("acon-mock", "valorant", "demo-create"));
  });
});
