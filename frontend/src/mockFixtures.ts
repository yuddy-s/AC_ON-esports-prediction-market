import type { Fixture, ResultObservation } from "./fixturesApi";

// Fictional fixtures in the backend's response shape, used when
// VITE_FIXTURE_SOURCE=mock (no backend needed). Not real matches or results.

const EVIDENCE = "https://example.org/acon-mock/";
const hash = (n: number) => `0x${n.toString(16).padStart(64, "0")}`;

function fixture(
  id: number,
  game: string,
  start: string,
  status: Fixture["match_status"],
  teams: [string, string],
  extra: Partial<Fixture> = {},
): Fixture {
  const [a, b] = teams;
  return {
    id,
    provider_id: "acon-mock",
    game_id: game,
    external_match_id: `demo-${id}`,
    scheduled_start: start,
    match_status: status,
    team_a_id: a.toLowerCase().replace(/\s+/g, "-"),
    team_a_name: a,
    team_b_id: b.toLowerCase().replace(/\s+/g, "-"),
    team_b_name: b,
    evidence_url: `${EVIDENCE}demo-${id}`,
    evidence_hash: hash(id),
    source_updated_at: "2026-10-30T12:00:00Z",
    imported_at: "2026-10-30T12:05:00Z",
    latest_result: null,
    registration_request_status: null,
    authoritative: false,
    ...extra,
  };
}

const result = (id: number, status: ResultObservation["match_status"], winner: string | null): ResultObservation => ({
  id,
  match_status: status,
  winner_team_id: winner,
  source_updated_at: "2026-11-02T21:00:00Z",
  evidence_url: `${EVIDENCE}result-${id}`,
  evidence_hash: hash(1000 + id),
  imported_at: "2026-11-02T21:10:00Z",
});

export const MOCK_RESULTS: Record<number, ResultObservation[]> = {
  4: [result(1, "completed", "mock-gamma")],
  5: [result(2, "canceled", null)],
};

export const MOCK_FIXTURES: Fixture[] = [
  fixture(1, "valorant", "2026-11-20T18:00:00Z", "scheduled", ["Mock Alpha", "Mock Bravo"]),
  fixture(2, "cs2", "2026-11-21T20:00:00Z", "scheduled", ["Mock Charlie", "Mock Delta"], {
    registration_request_status: "awaiting_abi",
  }),
  fixture(3, "lol", "2026-11-22T16:00:00Z", "postponed", ["Mock Echo", "Mock Foxtrot"]),
  fixture(4, "valorant", "2026-11-02T18:00:00Z", "completed", ["Mock Gamma", "Mock Hotel"], {
    latest_result: MOCK_RESULTS[4][0],
  }),
  fixture(5, "cs2", "2026-11-02T19:00:00Z", "canceled", ["Mock India", "Mock Juliet"], {
    latest_result: MOCK_RESULTS[5][0],
  }),
];
