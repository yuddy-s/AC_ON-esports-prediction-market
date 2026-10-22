export { predictionMarketAbi } from "./abi/predictionMarketAbi";
export { aconTokenAbi } from "./abi/aconTokenAbi";

// Frozen order from docs/agent/interfaces/M3_TRADING_INTERFACE.md.
// Index = the uint8 value the contract returns.
export const MARKET_STATES = [
  "CREATED",
  "OPEN",
  "CLOSED",
  "PROPOSED",
  "DISPUTED",
  "FINALIZED",
  "VOID",
] as const;

export const MARKET_STATE_OPEN = 1;

// Outcome enum: YES = 0, NO = 1.
export const OUTCOME = { YES: 0, NO: 1 } as const;
export type Outcome = (typeof OUTCOME)[keyof typeof OUTCOME];

// LMSR limit frozen in the decision record (1e18 base units).
export const MAX_SHARES_PER_TRADE = 100n * 10n ** 18n;
