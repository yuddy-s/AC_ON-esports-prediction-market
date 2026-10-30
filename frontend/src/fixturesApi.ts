import { API_URL, FIXTURE_SOURCE } from "./config";
import { MOCK_FIXTURES, MOCK_RESULTS } from "./mockFixtures";

// Read-only client for the backend fixture catalog (docs/agent/interfaces/
// M4_BACKEND_API.md). Fixtures are imported off-chain source data: a fixture
// is not a registered fixture or a market, and nothing here settles anything.

export type MatchStatus =
  | "scheduled"
  | "live"
  | "postponed"
  | "completed"
  | "canceled"
  | "tied"
  | "no_contest"
  | "unsupported";

export type RegistrationStatus =
  | "awaiting_abi"
  | "queued"
  | "retryable_failure"
  | "submitted"
  | "submission_unknown"
  | "terminal_failure"
  | "confirmed";

export interface ResultObservation {
  id: number;
  match_status: MatchStatus;
  winner_team_id: string | null;
  source_updated_at: string;
  evidence_url: string;
  evidence_hash: string;
  imported_at: string;
}

export interface Fixture {
  id: number;
  provider_id: string;
  game_id: string;
  external_match_id: string;
  scheduled_start: string;
  match_status: MatchStatus;
  team_a_id: string;
  team_a_name: string;
  team_b_id: string;
  team_b_name: string;
  evidence_url: string | null;
  evidence_hash: string | null;
  source_updated_at: string;
  imported_at: string;
  latest_result: ResultObservation | null;
  registration_request_status: RegistrationStatus | null;
  authoritative: false;
}

export interface FixturePage {
  items: Fixture[];
  total: number;
  limit: number;
  offset: number;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { signal });
  if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
  return (await response.json()) as T;
}

// registration_request_status arrives with the registration API (#31); an
// older backend omits it, which means no request.
export function normalizeFixture(raw: Fixture): Fixture {
  return { ...raw, registration_request_status: raw.registration_request_status ?? null };
}

// The API caps a page at 100; the M4 catalog is a short curated list.
export async function fetchFixtures(signal?: AbortSignal): Promise<FixturePage> {
  if (FIXTURE_SOURCE === "mock") {
    return { items: MOCK_FIXTURES, total: MOCK_FIXTURES.length, limit: 100, offset: 0 };
  }
  const page = await getJson<FixturePage>("/api/fixtures?limit=100&offset=0", signal);
  return { ...page, items: page.items.map(normalizeFixture) };
}

// Resolves to null on 404 so the page can say "not found" instead of failing.
export async function fetchFixture(id: number, signal?: AbortSignal): Promise<Fixture | null> {
  if (FIXTURE_SOURCE === "mock") return MOCK_FIXTURES.find((f) => f.id === id) ?? null;
  const response = await fetch(`${API_URL}/api/fixtures/${id}`, { signal });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`/api/fixtures/${id} returned HTTP ${response.status}`);
  return normalizeFixture((await response.json()) as Fixture);
}

// All source observations, oldest first. A later observation can disagree
// with an earlier one; both stay visible.
export async function fetchFixtureResults(id: number, signal?: AbortSignal): Promise<ResultObservation[]> {
  if (FIXTURE_SOURCE === "mock") return MOCK_RESULTS[id] ?? [];
  return getJson<ResultObservation[]>(`/api/fixtures/${id}/results`, signal);
}
