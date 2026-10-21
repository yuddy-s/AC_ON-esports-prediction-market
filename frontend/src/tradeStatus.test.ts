import { describe, expect, it } from "vitest";
import { isBusy, isFailure, statusMessage, stepIndex, TRADE_STEPS, type TradeStatus } from "./tradeStatus";

const hash = `0x${"ab".repeat(32)}` as const;
const trade = {
  market_id: 0,
  trader: "0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
  outcome: 0,
  shares: "10000000000000000000",
  cost: "5249584441082326050",
  yes_quantity: "10000000000000000000",
  no_quantity: "0",
  block_number: 527,
  transaction_hash: hash,
  log_index: 2,
};

const statuses: Record<TradeStatus["kind"], TradeStatus> = {
  idle: { kind: "idle" },
  "approve-wallet": { kind: "approve-wallet" },
  "approve-pending": { kind: "approve-pending", hash },
  "buy-wallet": { kind: "buy-wallet" },
  submitted: { kind: "submitted", hash },
  mined: { kind: "mined", hash, blockNumber: 527n, indexer: { state: "waiting", lastSafeBlock: 520 } },
  indexed: { kind: "indexed", hash, blockNumber: 527n, trade },
  reverted: { kind: "reverted", hash },
  rejected: { kind: "rejected" },
  error: { kind: "error", message: "Not enough ACON for this trade." },
};

describe("submitted, mined and indexed are separate states", () => {
  it("each sits on its own progress step", () => {
    expect(TRADE_STEPS).toEqual(["Wallet", "Submitted", "Mined", "Indexed"]);
    expect(stepIndex(statuses["buy-wallet"])).toBe(0);
    expect(stepIndex(statuses.submitted)).toBe(1);
    expect(stepIndex(statuses.mined)).toBe(2);
    expect(stepIndex(statuses.indexed)).toBe(3);
  });

  it("a mined trade is not reported as indexed", () => {
    expect(statusMessage(statuses.mined)).toMatch(/^Mined in block 527\./);
    expect(statusMessage(statuses.mined)).toMatch(/Waiting for the indexer \(indexed up to block 520\)/);
    expect(statusMessage(statuses.mined)).not.toMatch(/Indexed:/);
    expect(statusMessage(statuses.indexed)).toBe("Indexed: the backend now shows your trade.");
  });

  it("every state has its own message", () => {
    const messages = Object.values(statuses)
      .filter((s) => s.kind !== "idle")
      .map(statusMessage);
    expect(new Set(messages).size).toBe(messages.length);
  });
});

describe("indexer problems keep the trade marked as mined", () => {
  const mined = (indexer: Extract<TradeStatus, { kind: "mined" }>["indexer"]): TradeStatus => ({
    kind: "mined",
    hash,
    blockNumber: 527n,
    indexer,
  });

  it("API unreachable", () => {
    expect(statusMessage(mined({ state: "unavailable", detail: "Failed to fetch" }))).toMatch(
      /on-chain, but the indexer API can't be reached yet \(Failed to fetch\)\. Retrying/,
    );
  });

  it("no API configured", () => {
    expect(statusMessage(mined({ state: "not-configured" }))).toMatch(/No indexer API configured/);
  });

  it("indexer timed out", () => {
    expect(statusMessage(mined({ state: "timed-out" }))).toMatch(/after 3 minutes/);
  });
});

describe("unhappy paths", () => {
  it("reverted, rejected and errors are failures; nothing else is", () => {
    const failures = Object.values(statuses).filter(isFailure).map((s) => s.kind);
    expect(failures.sort()).toEqual(["error", "rejected", "reverted"]);
  });

  it("a reverted transaction says no ACON was spent", () => {
    expect(statusMessage(statuses.reverted)).toMatch(/reverted\. No ACON was spent/);
  });

  it("an error shows its message", () => {
    expect(statusMessage(statuses.error)).toBe("Not enough ACON for this trade.");
  });
});

describe("isBusy locks the form only while waiting on the wallet or chain", () => {
  it.each([
    ["approve-wallet", true],
    ["approve-pending", true],
    ["buy-wallet", true],
    ["submitted", true],
    ["idle", false],
    ["mined", false],
    ["indexed", false],
    ["reverted", false],
    ["rejected", false],
    ["error", false],
  ] as const)("%s → %s", (kind, busy) => {
    expect(isBusy(statuses[kind])).toBe(busy);
  });
});
