import { describe, expect, it } from "vitest";
import {
  ContractFunctionExecutionError,
  ContractFunctionRevertedError,
  encodeErrorResult,
  UserRejectedRequestError,
} from "viem";
import { describeContractError, describeError, isUserRejection } from "./errors";
import { predictionMarketAbi } from "./predictionMarket";

// Builds the same error shape viem throws when buy() reverts with a custom error.
function revert(errorName: string, args?: readonly unknown[]) {
  const data = encodeErrorResult({ abi: predictionMarketAbi, errorName, args } as Parameters<typeof encodeErrorResult>[0]);
  const cause = new ContractFunctionRevertedError({ abi: predictionMarketAbi, data, functionName: "buy" });
  return new ContractFunctionExecutionError(cause, {
    abi: predictionMarketAbi,
    functionName: "buy",
    args: [0n, 0, 10n * 10n ** 18n, 6n * 10n ** 18n],
  });
}

describe("describeError: contract reverts are decoded by error name", () => {
  it("slippage shows the actual cost and the user's max", () => {
    const message = describeError(revert("SlippageExceeded", [5_801_200_000_000_000_000n, 5_302_000_000_000_000_000n]));
    expect(message).toBe(
      "The price moved: the trade now costs 5.8 ACON, above your max of 5.3 ACON. Get a new quote or raise your slippage.",
    );
  });

  it("deadline passed", () => {
    expect(describeError(revert("TradingClosed"))).toBe("Trading has closed for this market (the deadline has passed).");
  });

  it("low balance", () => {
    expect(describeError(revert("InsufficientTokenBalance", [10n, 1n]))).toMatch(/^Not enough ACON/);
  });

  it("LMSR limits propagated from the library", () => {
    expect(describeError(revert("TradeSizeLimitExceeded", [150n * 10n ** 18n, 100n * 10n ** 18n]))).toBe(
      "Max 100 shares per trade.",
    );
    expect(describeError(revert("TradeTooSmall"))).toMatch(/too small/);
  });
});

describe("wallet rejection", () => {
  const rejected = new UserRejectedRequestError(new Error("User rejected the request."));

  it("is detected", () => {
    expect(isUserRejection(rejected)).toBe(true);
    expect(isUserRejection(new Error("boom"))).toBe(false);
  });

  it("gets its own message", () => {
    expect(describeError(rejected)).toBe("You rejected the request in your wallet.");
  });
});

describe("describeContractError", () => {
  it("covers every custom error in the PredictionMarket ABI", () => {
    const names = predictionMarketAbi
      .filter((item) => item.type === "error" && !item.name.startsWith("PRBMath_"))
      .map((item) => (item as { name: string }).name);
    for (const name of names) {
      expect(describeContractError(name), name).not.toMatch(/rejected the transaction/);
    }
  });

  it("falls back to the raw error name for unknown errors", () => {
    expect(describeContractError("SomethingNew")).toBe("The contract rejected the transaction (SomethingNew).");
  });
});

describe("describeError: other errors", () => {
  it("uses the message of a plain Error", () => {
    expect(describeError(new Error("network down"))).toBe("network down");
  });
});
