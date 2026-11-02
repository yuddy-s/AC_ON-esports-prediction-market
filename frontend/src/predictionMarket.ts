import { linkedErrorsAbi } from "./abi/linkedErrorsAbi";
import { predictionMarketAbi as marketAbi } from "./abi/predictionMarketAbi";

// Market ABI plus the pricing/token errors that can revert through it
// (CONTRACT_ABI.md: decode reverts with the market, pricing and token errors).
export const predictionMarketAbi = [...marketAbi, ...linkedErrorsAbi] as const;
export { aconTokenAbi } from "./abi/aconTokenAbi";

// Stored M4 state order from docs/agent/interfaces/CONTRACT_ABI.md.
// Index = the uint8 value the contract returns.
export const MARKET_STATES = [
  "OPEN",
  "CLOSED",
  "PROPOSED",
  "DISPUTED",
  "RESOLVER_SELECTION",
  "RESOLVER_VOTING",
  "FINALIZED",
  "VOID",
] as const;

export const MARKET_STATE = {
  OPEN: 0,
  CLOSED: 1,
  PROPOSED: 2,
  DISPUTED: 3,
  RESOLVER_SELECTION: 4,
  RESOLVER_VOTING: 5,
  FINALIZED: 6,
  VOID: 7,
} as const;

export const MARKET_STATE_OPEN = MARKET_STATE.OPEN;

// Short labels for lists; the market page uses marketPhase() for detail.
export const STATE_LABELS = ["Closed", "Closed", "Proposed", "Disputed", "Selecting resolvers", "Resolver vote", "Final", "Void"] as const;

// Trade outcome: YES = 0 (Team A), NO = 1 (Team B).
export const OUTCOME = { YES: 0, NO: 1 } as const;
export type Outcome = (typeof OUTCOME)[keyof typeof OUTCOME];

// Proposal / vote choice: YES = 0, NO = 1, VOID = 2.
export const CHOICE = { YES: 0, NO: 1, VOID: 2 } as const;
export type Choice = (typeof CHOICE)[keyof typeof CHOICE];
export const CHOICE_LABELS = ["YES", "NO", "VOID"] as const;

// Limits and amounts from the ABI document (1e18 base units, Unix seconds).
export const MAX_SHARES_PER_TRADE = 100n * 10n ** 18n;
export const REQUIRED_SUBSIDY = 34_657_359_027_997_265_471n;
export const CHALLENGE_BOND = 10n * 10n ** 18n;
export const MIN_START_MARGIN_SECONDS = 900n;
export const NO_PROPOSAL_PERIOD_SECONDS = 604_800n;
export const RETRY_DELAY_SECONDS = 1_800n;
