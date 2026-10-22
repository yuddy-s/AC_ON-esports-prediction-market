import { formatUnits } from "viem";

// Formats a base-unit amount (e.g. 1e18 = 1 ACON) for display without going
// through floating point: "1234567.891" -> "1,234,567.89".
export function formatTokenAmount(amount: bigint, decimals = 18, maxFractionDigits = 2): string {
  const negative = amount < 0n;
  const [whole, fraction = ""] = formatUnits(negative ? -amount : amount, decimals).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const trimmed = fraction.slice(0, maxFractionDigits).replace(/0+$/, "");
  return `${negative ? "-" : ""}${grouped}${trimmed ? `.${trimmed}` : ""}`;
}

export function shortenAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

// 0.6234 -> "62.3%"
export function formatPercent(probability: number): string {
  return `${(probability * 100).toFixed(1)}%`;
}
