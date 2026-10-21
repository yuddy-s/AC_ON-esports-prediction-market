import { parseUnits } from "viem";
import { MAX_SHARES_PER_TRADE } from "./predictionMarket";

export type ParsedShares = { ok: true; value: bigint } | { ok: false; error: string };

// "12.5" -> 12.5e18 base units, with the contract's per-trade limit applied.
export function parseShares(input: string): ParsedShares {
  const text = input.trim();
  if (text === "") return { ok: false, error: "Enter a number of shares." };
  if (!/^\d*\.?\d*$/.test(text) || text === ".") return { ok: false, error: "Shares must be a positive number." };
  const [, fraction = ""] = text.split(".");
  if (fraction.length > 18) return { ok: false, error: "Use at most 18 decimal places." };
  const value = parseUnits(text, 18);
  if (value === 0n) return { ok: false, error: "Shares must be greater than 0." };
  if (value > MAX_SHARES_PER_TRADE) return { ok: false, error: "Max 100 shares per trade." };
  return { ok: true, value };
}

// Slippage guard: the most the user agrees to pay if the price moves between
// the quote and the transaction being mined. Rounded up so maxCost >= quote.
export function computeMaxCost(quote: bigint, slippageBps: number): bigint {
  if (!Number.isInteger(slippageBps) || slippageBps < 0) throw new Error("slippageBps must be a non-negative integer");
  const numerator = quote * BigInt(10_000 + slippageBps);
  return (numerator + 9_999n) / 10_000n;
}

// "1" (%) -> 100 basis points. Returns undefined for invalid input.
export function parseSlippagePercent(input: string): number | undefined {
  const value = Number(input);
  if (input.trim() === "" || !Number.isFinite(value) || value < 0 || value > 50) return undefined;
  return Math.round(value * 100);
}

// The backend serialises 1e18 base-unit Decimals as JSON strings, possibly as
// "10000000000000000000", "10000000000000000000.0" or "1E+19".
export function parseBaseUnits(value: string | number): bigint {
  const text = String(value).trim();
  const match = /^(\d+)(?:\.(\d*))?(?:[eE]\+?(\d+))?$/.exec(text);
  if (!match) throw new Error(`Not a base-unit amount: ${text}`);
  const [, whole, fraction = "", exponent = "0"] = match;
  const shift = Number(exponent);
  const digits = whole + fraction.padEnd(shift, "0");
  const integerDigits = whole.length + shift;
  const integerPart = digits.slice(0, integerDigits);
  if (/[1-9]/.test(digits.slice(integerDigits))) throw new Error(`Fractional base units: ${text}`);
  return BigInt(integerPart || "0");
}
