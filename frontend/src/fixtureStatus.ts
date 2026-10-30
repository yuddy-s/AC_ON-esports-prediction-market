import type { Fixture, MatchStatus, RegistrationStatus } from "./fixturesApi";

// Pure display rules for the fixture catalog. The backend and contract stay
// authoritative; these only decide what the UI says and offers.

export type Tone = "neutral" | "good" | "warn" | "bad";

export const MATCH_STATUS_LABELS: Record<MatchStatus, string> = {
  scheduled: "Scheduled",
  live: "Live",
  postponed: "Postponed",
  completed: "Completed",
  canceled: "Canceled",
  tied: "Tied",
  no_contest: "No contest",
  unsupported: "Unsupported result",
};

export function matchStatusTone(status: MatchStatus): Tone {
  if (status === "scheduled") return "good";
  if (status === "live" || status === "postponed") return "warn";
  if (status === "completed") return "neutral";
  return "bad";
}

export interface RegistrationView {
  label: string;
  tone: Tone;
  detail: string;
}

// Only "confirmed" means the fixture is registered on-chain. Every other job
// status means a market cannot be created yet (M4_BACKEND_API.md).
export function describeRegistration(status: RegistrationStatus | null): RegistrationView {
  switch (status) {
    case null:
      return { label: "Not registered", tone: "neutral", detail: "No one has requested on-chain registration for this fixture." };
    case "awaiting_abi":
      return {
        label: "Requested",
        tone: "warn",
        detail: "Registration was requested, but the M4 contract is not deployed yet, so nothing has been written on-chain.",
      };
    case "queued":
      return { label: "Queued", tone: "warn", detail: "Waiting for the registrar to submit the registration." };
    case "retryable_failure":
      return { label: "Retrying", tone: "warn", detail: "The registrar's last attempt failed and will be retried." };
    case "submitted":
      return { label: "Submitted", tone: "warn", detail: "The registration transaction was sent and is waiting for confirmations." };
    case "submission_unknown":
      return {
        label: "Checking",
        tone: "warn",
        detail: "The registrar is not sure the registration was sent. It is checked before anything is resent.",
      };
    case "terminal_failure":
      return {
        label: "Failed",
        tone: "bad",
        detail: "Registration failed. Depending on the cause, it needs a new signed request or a fix from a team operator.",
      };
    case "confirmed":
      return { label: "Registered", tone: "good", detail: "Registered on-chain. A market can be created for this fixture." };
  }
}

export function canCreateMarket(status: RegistrationStatus | null): boolean {
  return status === "confirmed";
}

export const MIN_LEAD_MINUTES = 30;

export type Eligibility = { ok: true } | { ok: false; reason: string };

// Terminal failures the backend lets a player re-authorize with a fresh
// signature (registration_service.REAUTHORIZABLE_FAILURES). Submitted,
// uncertain and confirmed jobs are never replaced.
export const REAUTHORIZABLE_FAILURES = new Set([
  "fixture_changed",
  "fixture_ineligible",
  "transaction_reverted",
  "attempts_exhausted",
]);

export interface JobSummary {
  status: RegistrationStatus;
  error_code: string | null;
}

// Whether a new signed request is allowed given the fixture's current job.
// The catalog only carries the job status, so a terminal failure needs the
// job itself (its error_code) to decide.
export function allowsNewRequest(status: RegistrationStatus | null, job: JobSummary | null | undefined): boolean {
  if (status === null) return true;
  if (status !== "terminal_failure") return false;
  return job?.status === "terminal_failure" && job.error_code !== null && REAUTHORIZABLE_FAILURES.has(job.error_code);
}

// Mirrors the backend's registration preconditions so the UI can explain why
// a fixture cannot be requested. The backend still re-checks everything.
export function registrationEligibility(fixture: Fixture, nowMs: number, job?: JobSummary | null): Eligibility {
  if (!allowsNewRequest(fixture.registration_request_status, job)) {
    return { ok: false, reason: "A registration request already exists for this fixture." };
  }
  if (fixture.match_status !== "scheduled") {
    return { ok: false, reason: `Only scheduled matches can be registered (this one is ${MATCH_STATUS_LABELS[fixture.match_status].toLowerCase()}).` };
  }
  if (fixture.latest_result !== null) {
    return { ok: false, reason: "This match already has a recorded result." };
  }
  if (!fixture.evidence_url || !fixture.evidence_hash || fixture.team_a_id === fixture.team_b_id) {
    return { ok: false, reason: "This fixture has no organizer evidence." };
  }
  // Strict, like the backend: a start exactly 30 minutes away is too near.
  const minutesLeft = (Date.parse(fixture.scheduled_start) - nowMs) / 60_000;
  if (minutesLeft <= MIN_LEAD_MINUTES) {
    return { ok: false, reason: `Registration closes ${MIN_LEAD_MINUTES} minutes before the scheduled start.` };
  }
  return { ok: true };
}

// YES is Team A and NO is Team B (M4 design decision).
export function outcomeTeams(fixture: Fixture): { yes: string; no: string } {
  return { yes: fixture.team_a_name, no: fixture.team_b_name };
}

export function winnerName(fixture: Fixture, winnerTeamId: string | null): string | null {
  if (winnerTeamId === fixture.team_a_id) return fixture.team_a_name;
  if (winnerTeamId === fixture.team_b_id) return fixture.team_b_name;
  return null;
}

export function gameLabel(gameId: string): string {
  const known: Record<string, string> = { valorant: "Valorant", cs2: "Counter-Strike 2", lol: "League of Legends", dota2: "Dota 2" };
  return known[gameId] ?? gameId;
}
