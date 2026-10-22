import { useEffect, useState } from "react";

// Current Unix time in seconds, refreshed on an interval so deadline checks
// update without a page reload.
export function useNowSeconds(intervalMs = 5_000): number {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now() / 1000), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
