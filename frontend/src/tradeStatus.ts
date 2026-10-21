import type { Hash } from "viem";
import type { IndexedTrade } from "./indexerApi";

// Submitted, mined and indexed are different moments (M2 feedback + M3
// decision record), so each gets its own state. Pure: no React or wallet.
export type IndexerWait =
  | { state: "waiting"; lastSafeBlock: number | null }
  | { state: "unavailable"; detail: string }
  | { state: "not-configured" }
  | { state: "timed-out" };

export type TradeStatus =
  | { kind: "idle" }
  | { kind: "approve-wallet" }
  | { kind: "approve-pending"; hash: Hash }
  | { kind: "buy-wallet" }
  | { kind: "submitted"; hash: Hash }
  | { kind: "mined"; hash: Hash; blockNumber: bigint; indexer: IndexerWait }
  | { kind: "indexed"; hash: Hash; blockNumber: bigint; trade: IndexedTrade }
  | { kind: "reverted"; hash: Hash }
  | { kind: "rejected" }
  | { kind: "error"; message: string };

export const TRADE_STEPS = ["Wallet", "Submitted", "Mined", "Indexed"] as const;

// True while a transaction is waiting on the wallet or the chain; inputs and
// the buy button are locked.
export function isBusy(status: TradeStatus): boolean {
  return ["approve-wallet", "approve-pending", "buy-wallet", "submitted"].includes(status.kind);
}

export function isFailure(status: TradeStatus): boolean {
  return status.kind === "reverted" || status.kind === "rejected" || status.kind === "error";
}

// Which of TRADE_STEPS the status is on (-1 = no progress bar).
export function stepIndex(status: TradeStatus): number {
  switch (status.kind) {
    case "approve-wallet":
    case "approve-pending":
    case "buy-wallet":
      return 0;
    case "submitted":
      return 1;
    case "mined":
    case "reverted":
      return 2;
    case "indexed":
      return 3;
    default:
      return -1;
  }
}

export function statusMessage(status: TradeStatus): string {
  switch (status.kind) {
    case "idle":
      return "";
    case "approve-wallet":
      return "Step 1 of 2: confirm the ACON approval in your wallet…";
    case "approve-pending":
      return "Approval submitted, waiting for it to be mined…";
    case "buy-wallet":
      return "Confirm the buy in your wallet…";
    case "submitted":
      return "Submitted. Waiting for the transaction to be mined…";
    case "mined":
      switch (status.indexer.state) {
        case "waiting":
          return `Mined in block ${status.blockNumber}. Your shares are on-chain. Waiting for the indexer${
            status.indexer.lastSafeBlock !== null ? ` (indexed up to block ${status.indexer.lastSafeBlock})` : ""
          }…`;
        case "unavailable":
          return `Mined in block ${status.blockNumber}. Your shares are on-chain, but the indexer API can't be reached yet (${status.indexer.detail}). Retrying…`;
        case "not-configured":
          return `Mined in block ${status.blockNumber}. Your shares are on-chain. (No indexer API configured, so the indexed step is skipped.)`;
        case "timed-out":
          return `Mined in block ${status.blockNumber}. Your shares are on-chain, but the indexer has not picked up the trade after 3 minutes.`;
      }
      return "";
    case "indexed":
      return "Indexed: the backend now shows your trade.";
    case "reverted":
      return "The transaction was mined but reverted. No ACON was spent on the trade and your position did not change.";
    case "rejected":
      return "You rejected the request in your wallet. Nothing was sent.";
    case "error":
      return status.message;
  }
}
