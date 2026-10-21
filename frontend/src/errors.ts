import { BaseError, ContractFunctionRevertedError, UserRejectedRequestError } from "viem";
import { formatTokenAmount } from "./format";

export function isUserRejection(error: unknown): boolean {
  if (error instanceof BaseError) {
    return error.walk((e) => e instanceof UserRejectedRequestError) instanceof UserRejectedRequestError;
  }
  return false;
}

// Maps the contracts' custom errors (by name, never by free-form strings) to
// messages a user can act on. See contracts/README.md "Reverts and limits".
export function describeContractError(errorName: string, args: readonly unknown[] = []): string {
  const amount = (i: number) => (typeof args[i] === "bigint" ? `${formatTokenAmount(args[i] as bigint)} ACON` : "?");
  switch (errorName) {
    case "TradingClosed":
      return "Trading has closed for this market (the deadline has passed).";
    case "MarketNotOpen":
      return "This market is not open for trading.";
    case "MarketNotFound":
      return "This market does not exist on the connected network.";
    case "SlippageExceeded":
      return `The price moved: the trade now costs ${amount(0)}, above your max of ${amount(1)}. Get a new quote or raise your slippage.`;
    case "InsufficientTokenBalance":
    case "InsufficientBalance":
      return "Not enough ACON for this trade. Claim from the faucet or buy fewer shares.";
    case "InsufficientTokenAllowance":
    case "InsufficientAllowance":
      return "The market is not approved to spend enough ACON. Approve again and retry.";
    case "ZeroShares":
      return "Shares must be greater than 0.";
    case "TradeTooSmall":
      return "This trade is too small to price. Buy more shares.";
    case "TradeSizeLimitExceeded":
      return "Max 100 shares per trade.";
    case "QuantityLimitExceeded":
      return "This market has reached its share limit for that outcome.";
    case "PaymentTransferFailed":
      return "The ACON payment transfer failed.";
    case "FaucetAlreadyClaimed":
      return "This wallet already claimed the faucet.";
    case "ReentrantCall":
      return "The contract rejected a re-entrant call.";
    default:
      return `The contract rejected the transaction (${errorName}).`;
  }
}

export function describeError(error: unknown): string {
  if (isUserRejection(error)) return "You rejected the request in your wallet.";
  if (error instanceof BaseError) {
    const reverted = error.walk((e) => e instanceof ContractFunctionRevertedError);
    if (reverted instanceof ContractFunctionRevertedError && reverted.data?.errorName) {
      return describeContractError(reverted.data.errorName, reverted.data.args ?? []);
    }
    return error.shortMessage;
  }
  return error instanceof Error ? error.message : String(error);
}
