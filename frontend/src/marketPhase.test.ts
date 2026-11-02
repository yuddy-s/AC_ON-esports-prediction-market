import { describe, expect, it } from "vitest";
import { marketPhase, type ResolutionView, type RoundView } from "./marketPhase";
import { MARKET_STATE } from "./predictionMarket";

const DEADLINE = 1_000_000n;
const DAY = 86_400;

const resolution = (extra: Partial<ResolutionView> = {}): ResolutionView => ({
  proposed: true,
  proposal: 1,
  proposer: "0xproposer",
  challengeDeadline: DEADLINE + 2n * 86_400n,
  challenger: "0x0000000000000000000000000000000000000000",
  round: 0,
  terminal: false,
  finalOutcome: 0,
  ...extra,
});

const round = (extra: Partial<RoundView> = {}): RoundView => ({
  selectionDeadline: DEADLINE + 8n * 86_400n,
  voteDeadline: DEADLINE + 4n * 86_400n,
  lastRequestAt: DEADLINE + 86_400n,
  hasRequest: true,
  fulfilled: false,
  ...extra,
});

const phase = (state: number, now: number, r?: ResolutionView, rr?: RoundView) =>
  marketPhase({ state, tradingDeadline: DEADLINE }, r, rr, now);

describe("marketPhase: trading and the deadline", () => {
  it("trades only while OPEN and before the deadline", () => {
    expect(phase(MARKET_STATE.OPEN, 999_999).actions).toEqual(["trade"]);
  });

  it("treats an OPEN market at or past its deadline as closed, never tradable", () => {
    const p = phase(MARKET_STATE.OPEN, 1_000_000);
    expect(p.key).toBe("awaiting-proposal");
    expect(p.actions).not.toContain("trade");
  });

  it("opens permissionless resolver selection seven days after the deadline", () => {
    expect(phase(MARKET_STATE.CLOSED, 1_000_000 + 7 * DAY - 1).actions).toEqual([]);
    expect(phase(MARKET_STATE.CLOSED, 1_000_000 + 7 * DAY).actions).toEqual(["request-selection"]);
    expect(phase(MARKET_STATE.OPEN, 1_000_000 + 7 * DAY).key).toBe("no-proposal");
  });
});

describe("marketPhase: proposal and challenge", () => {
  it("allows a challenge strictly before the challenge deadline, then finalize", () => {
    const r = resolution();
    expect(phase(MARKET_STATE.PROPOSED, 1_000_000 + 2 * DAY - 1, r)).toMatchObject({ label: "Proposed: NO", actions: ["challenge"] });
    expect(phase(MARKET_STATE.PROPOSED, 1_000_000 + 2 * DAY, r).actions).toEqual(["finalize"]);
  });

  it("lets anyone start selection once disputed", () => {
    expect(phase(MARKET_STATE.DISPUTED, 0, resolution()).actions).toEqual(["request-selection"]);
  });
});

describe("marketPhase: resolver selection and voting", () => {
  it("waits for the VRF draw, then allows a retry after 30 minutes", () => {
    const rr = round();
    expect(phase(MARKET_STATE.RESOLVER_SELECTION, 1_000_000 + DAY + 1_799, resolution({ round: 1 }), rr).actions).toEqual([]);
    expect(phase(MARKET_STATE.RESOLVER_SELECTION, 1_000_000 + DAY + 1_800, resolution({ round: 1 }), rr).actions).toEqual(["retry-selection"]);
  });

  it("allows an immediate request when no request exists (pool too small or failed)", () => {
    expect(phase(MARKET_STATE.RESOLVER_SELECTION, 0, resolution({ round: 1 }), round({ hasRequest: false })).actions).toEqual(["retry-selection"]);
  });

  it("voids through advance once the selection deadline passes", () => {
    expect(phase(MARKET_STATE.RESOLVER_SELECTION, 1_000_000 + 8 * DAY, resolution({ round: 1 }), round()).actions).toEqual(["advance"]);
  });

  it("votes until the vote deadline, then advances to round 2 or VOID", () => {
    const rr = round({ fulfilled: true });
    expect(phase(MARKET_STATE.RESOLVER_VOTING, 1_000_000 + 4 * DAY - 1, resolution({ round: 1 }), rr).actions).toEqual(["vote"]);
    const r1 = phase(MARKET_STATE.RESOLVER_VOTING, 1_000_000 + 4 * DAY, resolution({ round: 1 }), rr);
    expect(r1.actions).toEqual(["advance"]);
    expect(r1.detail).toContain("replacement committee");
    expect(phase(MARKET_STATE.RESOLVER_VOTING, 1_000_000 + 4 * DAY, resolution({ round: 2 }), rr).detail).toContain("voids it");
  });
});

describe("marketPhase: settlement", () => {
  it("names the final outcome and offers the claim", () => {
    expect(phase(MARKET_STATE.FINALIZED, 0, resolution({ terminal: true, finalOutcome: 0 }))).toMatchObject({ label: "Final: YES", actions: ["claim"] });
    expect(phase(MARKET_STATE.VOID, 0, resolution({ terminal: true, finalOutcome: 2 }))).toMatchObject({ key: "void", actions: ["claim"] });
  });
});
