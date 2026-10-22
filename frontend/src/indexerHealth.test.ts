import { describe, expect, it } from "vitest";
import type { IndexerStatus } from "./indexerApi";
import { indexerDeploymentProblem, indexerIsStale } from "./indexerHealth";

const market = "0x1234567890abcdef1234567890abcdef12345678";
const status: IndexerStatus = {
  configured: true,
  chain_id: 11155111,
  contract_address: market.toUpperCase(),
  latest_observed_block: 600,
  last_safe_block: 598,
  lag_blocks: 2,
  updated_at: "2026-10-21T17:00:00Z",
};

describe("indexer deployment guard", () => {
  it("accepts only the active chain and market, ignoring address case", () => {
    expect(indexerDeploymentProblem(status, 11155111, market)).toBeNull();
    expect(indexerDeploymentProblem(status, 31337, market)).toMatch(/chain/);
    expect(indexerDeploymentProblem(status, 11155111, "0x0000000000000000000000000000000000000001")).toMatch(/different/);
    expect(indexerDeploymentProblem({ ...status, configured: false }, 11155111, market)).toMatch(/no active/);
    expect(indexerDeploymentProblem({ ...status, contract_address: null }, 11155111, market)).toMatch(/different/);
    expect(indexerDeploymentProblem(status, 11155111, undefined)).toMatch(/not configured/);
  });
});

describe("indexer worker freshness", () => {
  const updated = Date.parse(status.updated_at!);

  it("flags checkpoints older than two minutes while allowing normal confirmation lag", () => {
    expect(indexerIsStale(status, updated + 120_000)).toBe(false);
    expect(indexerIsStale(status, updated + 120_001)).toBe(true);
  });

  it("does not label a worker stale before its first observation", () => {
    expect(indexerIsStale({ ...status, updated_at: null }, updated + 300_000)).toBe(false);
  });
});
