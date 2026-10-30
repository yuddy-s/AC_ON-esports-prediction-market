import { describe, expect, it } from "vitest";
import type { Fixture, RegistrationStatus } from "./fixturesApi";
import {
  canCreateMarket,
  describeRegistration,
  outcomeTeams,
  registrationEligibility,
  winnerName,
} from "./fixtureStatus";

const START = "2026-11-20T18:00:00Z";
const startMs = Date.parse(START);

function fixture(extra: Partial<Fixture> = {}): Fixture {
  return {
    id: 1,
    provider_id: "acon-mock",
    game_id: "valorant",
    external_match_id: "demo-1",
    scheduled_start: START,
    match_status: "scheduled",
    team_a_id: "alpha",
    team_a_name: "Mock Alpha",
    team_b_id: "bravo",
    team_b_name: "Mock Bravo",
    evidence_url: "https://example.org/demo-1",
    evidence_hash: `0x${"1".padStart(64, "0")}`,
    source_updated_at: "2026-10-30T12:00:00Z",
    imported_at: "2026-10-30T12:05:00Z",
    latest_result: null,
    registration_request_status: null,
    authoritative: false,
    ...extra,
  };
}

describe("canCreateMarket", () => {
  it("allows market creation only after on-chain confirmation", () => {
    const statuses: (RegistrationStatus | null)[] = [
      null, "awaiting_abi", "queued", "retryable_failure", "submitted", "submission_unknown", "terminal_failure",
    ];
    for (const status of statuses) expect(canCreateMarket(status)).toBe(false);
    expect(canCreateMarket("confirmed")).toBe(true);
  });
});

describe("describeRegistration", () => {
  it("says nothing is on-chain while the M4 contract is missing", () => {
    expect(describeRegistration("awaiting_abi").detail).toContain("nothing has been written on-chain");
  });

  it("does not call an uncertain submission a failure", () => {
    const view = describeRegistration("submission_unknown");
    expect(view.tone).toBe("warn");
    expect(view.label).not.toMatch(/fail/i);
  });

  it("marks only confirmed as registered", () => {
    expect(describeRegistration("confirmed")).toMatchObject({ label: "Registered", tone: "good" });
    expect(describeRegistration(null).label).toBe("Not registered");
  });
});

describe("registrationEligibility", () => {
  const anHourBefore = startMs - 60 * 60_000;

  it("accepts a scheduled fixture with evidence and enough lead time", () => {
    expect(registrationEligibility(fixture(), anHourBefore)).toEqual({ ok: true });
  });

  it("closes 30 minutes before the scheduled start", () => {
    expect(registrationEligibility(fixture(), startMs - 30 * 60_000).ok).toBe(true);
    expect(registrationEligibility(fixture(), startMs - 29 * 60_000).ok).toBe(false);
  });

  it("rejects fixtures that are not scheduled, have a result, lack evidence, or were already requested", () => {
    const cases: Partial<Fixture>[] = [
      { match_status: "postponed" },
      { latest_result: { id: 1, match_status: "completed", winner_team_id: "alpha", source_updated_at: START, evidence_url: "https://example.org/r", evidence_hash: "0x00", imported_at: START } },
      { evidence_url: null, evidence_hash: null },
      { registration_request_status: "awaiting_abi" },
    ];
    for (const extra of cases) {
      const result = registrationEligibility(fixture(extra), anHourBefore);
      expect(result.ok).toBe(false);
    }
  });

  it("explains why a postponed match cannot be registered", () => {
    const result = registrationEligibility(fixture({ match_status: "postponed" }), anHourBefore);
    expect(result).toEqual({ ok: false, reason: "Only scheduled matches can be registered (this one is postponed)." });
  });
});

describe("outcomeTeams and winnerName", () => {
  it("maps YES to Team A and NO to Team B", () => {
    expect(outcomeTeams(fixture())).toEqual({ yes: "Mock Alpha", no: "Mock Bravo" });
  });

  it("names the winner only when it is one of the two teams", () => {
    expect(winnerName(fixture(), "bravo")).toBe("Mock Bravo");
    expect(winnerName(fixture(), null)).toBeNull();
    expect(winnerName(fixture(), "someone-else")).toBeNull();
  });
});
