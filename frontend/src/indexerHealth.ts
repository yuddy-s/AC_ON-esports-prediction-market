import type { IndexerStatus } from "./indexerApi";

// The API serves one active deployment. Its derived trades belong in this
// wallet view only when the active chain and market match the frontend.
export function indexerDeploymentProblem(
  status: IndexerStatus,
  chainId: number,
  marketAddress: string | undefined,
): string | null {
  if (!marketAddress) return "The market address is not configured in the frontend.";
  if (!status.configured) return "The indexer has no active market deployment.";
  if (status.chain_id !== chainId) return `The indexer is on chain ${status.chain_id}, but this page is on chain ${chainId}.`;
  if (status.contract_address?.toLowerCase() !== marketAddress.toLowerCase()) {
    return "The indexer is tracking a different PredictionMarket contract.";
  }
  return null;
}

// The two-confirmation lag is normal; an old checkpoint update means the
// worker has stopped polling entirely.
export function indexerIsStale(status: IndexerStatus, nowMs = Date.now()): boolean {
  if (!status.updated_at) return false;
  const updatedMs = Date.parse(status.updated_at);
  return !Number.isFinite(updatedMs) || nowMs - updatedMs > 2 * 60_000;
}
