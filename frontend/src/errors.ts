import { BaseError, ContractFunctionRevertedError, UserRejectedRequestError } from "viem";
import { formatTokenAmount } from "./format";

export function isUserRejection(error: unknown): boolean {
  if (error instanceof BaseError) {
    return error.walk((e) => e instanceof UserRejectedRequestError) instanceof UserRejectedRequestError;
  }
  return false;
}

// True only when the call reached the contract and it reverted with this
// custom error. RPC, network and decoding failures are not contract answers.
export function isContractRevert(error: unknown, errorName: string): boolean {
  if (!(error instanceof BaseError)) return false;
  const reverted = error.walk((e) => e instanceof ContractFunctionRevertedError);
  return reverted instanceof ContractFunctionRevertedError && reverted.data?.errorName === errorName;
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
    case "EmptyQuestion":
      return "A market needs a question.";
    case "InvalidTradingDeadline":
      return "The trading deadline must be in the future.";
    case "InvalidPaymentToken":
      return "The market was deployed without a valid payment token.";
    case "PaymentTransferFailed":
      return "The ACON payment transfer failed.";
    case "FaucetAlreadyClaimed":
      return "This wallet already claimed the faucet.";
    case "ReentrantCall":
      return "The contract rejected a re-entrant call.";
    // M4 lifecycle (docs/agent/interfaces/CONTRACT_ABI.md).
    case "MinimumReturnNotMet":
      return `The price moved: the sale now pays ${amount(0)}, below your minimum of ${amount(1)}. Get a new quote or raise your slippage.`;
    case "InsufficientShares":
      return "You don't own that many shares of this side.";
    case "WrongState":
      return "The market has moved to a different stage. Refresh and try again.";
    case "FixtureNotRegistered":
      return "This fixture is not registered on-chain yet.";
    case "FixtureRevisionMismatch":
      return "The registered fixture changed while you were creating the market. Review it and try again.";
    case "MarketAlreadyExists":
      return "A market already exists for this fixture.";
    case "FixtureLocked":
      return "This fixture's details are locked because its market is funded.";
    case "ChallengeWindowClosed":
      return "The 24-hour challenge window has closed.";
    case "ChallengeNotAllowed":
      return "The proposer can't challenge their own proposal.";
    case "ChallengeAlreadyExists":
      return "This proposal was already challenged (only the first challenge is accepted).";
    case "ResolverNotSelected":
      return "This wallet is not on the resolver committee for this round.";
    case "AlreadyVoted":
      return "This wallet already voted in this round.";
    case "VotingClosed":
      return "The voting period for this round has ended.";
    case "SelectionExpired":
      return "Resolver selection expired. Advance the market instead.";
    case "RetryTooSoon":
      return "The committee draw was requested less than 30 minutes ago. Try again later.";
    case "DeadlineNotReached":
      return "It's too early for this step.";
    case "ProposalExpired":
      return "The proposal window has passed.";
    case "NoPosition":
      return "This wallet holds no shares in this market.";
    case "AlreadyClaimed":
      return "This wallet already claimed its payout for this market.";
    case "NoSurplus":
      return "There is no creator surplus to withdraw yet.";
    case "CreatorOnly":
      return "Only the market creator can withdraw the surplus.";
    case "InsufficientCollateral":
      return "The market does not hold enough collateral for this payout.";
    case "UnexpectedTokenTransfer":
      return "The ACON transfer did not move the expected amount.";
    case "Unauthorized":
      return "This wallet does not have the role needed for this action.";
    case "InsufficientQuantity":
      return "The market doesn't have that many shares outstanding on this side.";
    case "PricingPrecisionExceeded":
      return "This trade size can't be priced precisely. Try a slightly different number of shares.";
    case "InvalidEvidence":
      return "Evidence is required (a non-empty link or reason).";
    case "InvalidFixture":
      return "The fixture details are invalid.";
    case "ProposalAlreadyExists":
      return "A result was already proposed for this market.";
    // Admin / VRF-coordinator paths; shown only if something is misconfigured.
    case "InvalidConfiguration":
    case "OnlyCoordinator":
    case "RequestIdCollision":
    case "UseAdministrationTransfer":
    case "ZeroAddress":
      return `This action is restricted to the contract's administrator or VRF coordinator (${errorName}).`;
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
