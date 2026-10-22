import { MARKET_STATE_OPEN } from "./predictionMarket";

// Fixed LMSR liquidity parameter b = 50e18 (docs/agent/interfaces/M3_TRADING_INTERFACE.md).
export const LMSR_B = 50n * 10n ** 18n;

// Display-only YES/NO prices from outstanding quantities. The contract has no
// public price function, so we use the LMSR formula
//   priceYes = 1 / (1 + exp((qNo - qYes) / b))
// in floating point. Trades never use this: the cost the user pays always
// comes from the contract's quoteBuy/buy.
export function lmsrPrices(yesQuantity: bigint, noQuantity: bigint): { yes: number; no: number } {
  const exponent = Number(noQuantity - yesQuantity) / Number(LMSR_B);
  const yes = 1 / (1 + Math.exp(exponent));
  return { yes, no: 1 - yes };
}

// M3 never stores CLOSED: an OPEN market at or after its deadline is not
// tradable (the contract reverts with TradingClosed).
export function isTradable(state: number, tradingDeadline: bigint, nowSeconds: number): boolean {
  return state === MARKET_STATE_OPEN && BigInt(Math.floor(nowSeconds)) < tradingDeadline;
}
