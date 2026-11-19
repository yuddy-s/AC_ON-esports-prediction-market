import { describe, expect, it } from "vitest";
import vectors from "../../docs/agent/testing/vectors/market_deadline_vectors.json";
import { isTradable } from "./lmsr";
import { marketPhase } from "./marketPhase";
import { MARKET_STATES } from "./predictionMarket";

// Issue #53: the same state/deadline vectors the contract and API tests use. The frontend must
// never offer a trade the contract would reject, and must derive "trading closed" from the stored
// state plus chain time, even while the stored state is still OPEN.

const stateIndex = (name: string) => {
  const i = MARKET_STATES.indexOf(name as (typeof MARKET_STATES)[number]);
  if (i < 0) throw new Error(`unknown state ${name}`);
  return i;
};

describe("shared market deadline vectors (#53)", () => {
  it("covers the deadline boundaries and the no-proposal timeout", () => {
    expect(vectors.noProposalPeriodSeconds).toBe(7 * 86_400);
    expect(vectors.vectors.length).toBeGreaterThanOrEqual(9);
  });

  for (const v of vectors.vectors) {
    it(`${v.name}: frontend tradability matches the contract`, () => {
      expect(isTradable(stateIndex(v.storedState), BigInt(v.tradingDeadline), v.blockTimestamp)).toBe(v.expected.tradeAccepted);
    });

    if ("frontendActions" in v.expected) {
      it(`${v.name}: effective phase offers only what the contract accepts`, () => {
        const phase = marketPhase(
          { state: stateIndex(v.storedState), tradingDeadline: BigInt(v.tradingDeadline) },
          undefined,
          undefined,
          v.blockTimestamp,
        );
        expect(phase.actions).toEqual(v.expected.frontendActions);
        expect(phase.actions.includes("trade")).toBe(v.expected.tradeAccepted);
        expect(phase.actions.includes("request-selection")).toBe(v.expected.noProposalSelectionAccepted);
      });
    }
  }
});
