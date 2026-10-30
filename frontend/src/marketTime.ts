// Countdown text for a trading deadline, e.g. "2d 4h", "3h 12m", "45m".
export function formatCountdown(deadlineSeconds: bigint, nowSeconds: number): string {
  const left = Number(deadlineSeconds) - Math.floor(nowSeconds);
  if (left <= 0) return "Closed";
  const days = Math.floor(left / 86_400);
  const hours = Math.floor((left % 86_400) / 3_600);
  const minutes = Math.floor((left % 3_600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return "<1m";
}
