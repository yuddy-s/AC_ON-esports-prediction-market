import { useQuery } from "@tanstack/react-query";
import { API_URL, FIXTURE_SOURCE } from "./config";
import { Badge } from "./Badge";
import { SourceNote } from "./FixtureCatalog";
import { fetchFixture, fetchFixtureResults, type Fixture, type ResultObservation } from "./fixturesApi";
import {
  allowsNewRequest,
  canCreateMarket,
  describeRegistration,
  gameLabel,
  MATCH_STATUS_LABELS,
  matchStatusTone,
  outcomeTeams,
  registrationEligibility,
  winnerName,
} from "./fixtureStatus";
import { shortenAddress } from "./format";
import { RegistrationRequest } from "./RegistrationRequest";
import { fetchRegistration } from "./registrationApi";
import { useNowSeconds } from "./useNow";

export function FixtureDetail({ id }: { id: number }) {
  const enabled = FIXTURE_SOURCE === "mock" || API_URL !== "";
  const fixture = useQuery({
    queryKey: ["fixture", FIXTURE_SOURCE, id],
    queryFn: ({ signal }) => fetchFixture(id, signal),
    enabled,
    refetchInterval: 15_000,
  });
  const results = useQuery({
    queryKey: ["fixture-results", FIXTURE_SOURCE, id],
    queryFn: ({ signal }) => fetchFixtureResults(id, signal),
    enabled: enabled && !!fixture.data,
  });

  return (
    <section className="rounded-lg border border-neutral-700 bg-neutral-900 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <a href="#/fixtures" className="text-xs text-amber-300 underline underline-offset-2">
          ← All fixtures
        </a>
        <SourceNote />
      </div>

      {fixture.isLoading && <p className="mt-4 text-sm text-neutral-400">Loading fixture…</p>}
      {fixture.isError && <p className="mt-4 text-sm text-red-400">Fixture catalog unavailable at {API_URL}.</p>}
      {fixture.data === null && <p className="mt-4 text-sm text-neutral-400">Fixture #{id} was not found.</p>}
      {fixture.data && <FixtureBody fixture={fixture.data} results={results.data} resultsFailed={results.isError} />}
    </section>
  );
}

function FixtureBody({
  fixture,
  results,
  resultsFailed,
}: {
  fixture: Fixture;
  results: ResultObservation[] | undefined;
  resultsFailed: boolean;
}) {
  const now = useNowSeconds(30_000);
  const teams = outcomeTeams(fixture);
  const registration = describeRegistration(fixture.registration_request_status);
  // The catalog only carries the job status; a terminal failure needs the
  // job's error_code to know whether a fresh signed request is allowed.
  const failed = fixture.registration_request_status === "terminal_failure";
  const job = useQuery({
    queryKey: ["fixture-registration", fixture.id],
    queryFn: ({ signal }) => fetchRegistration(fixture.id, signal),
    enabled: FIXTURE_SOURCE === "api" && failed,
    refetchInterval: 15_000,
  });
  const eligibility = registrationEligibility(fixture, now * 1000, job.data);

  return (
    <div className="mt-3 flex flex-col gap-4">
      <div>
        <p className="text-xs uppercase tracking-wide text-neutral-500">
          {gameLabel(fixture.game_id)} · fixture #{fixture.id}
        </p>
        <h2 className="mt-1 text-lg font-semibold text-neutral-100">
          {fixture.team_a_name} vs {fixture.team_b_name}
        </h2>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Badge tone={matchStatusTone(fixture.match_status)}>{MATCH_STATUS_LABELS[fixture.match_status]}</Badge>
          <span className="text-sm text-neutral-400">
            Scheduled start: {new Date(fixture.scheduled_start).toLocaleString()}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <OutcomeTile label="YES" team={teams.yes} accent="text-emerald-300" />
        <OutcomeTile label="NO" team={teams.no} accent="text-rose-300" />
      </div>

      <div className="rounded-md border border-neutral-800 bg-neutral-950 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Source and resolution</p>
        <p className="mt-1 text-sm text-neutral-300">
          The market resolves YES if {teams.yes} wins and NO if {teams.no} wins. A canceled, tied, no-contest or
          unsupported result is proposed as VOID. A proposed result can be challenged.
        </p>
        <p className="mt-2 text-xs text-neutral-500">
          Provider <span className="font-mono">{fixture.provider_id}</span>, match{" "}
          <span className="font-mono">{fixture.external_match_id}</span>
        </p>
        <Evidence url={fixture.evidence_url} hash={fixture.evidence_hash} />
      </div>

      <div className="rounded-md border border-neutral-800 bg-neutral-950 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">On-chain registration</p>
          <Badge tone={registration.tone}>{registration.label}</Badge>
        </div>
        <p className="mt-1 text-sm text-neutral-300">{registration.detail}</p>
        {failed && job.data && (
          <p className="mt-1 text-sm text-neutral-400">
            {allowsNewRequest(fixture.registration_request_status, job.data)
              ? "This failure can be retried with a new signed request."
              : "This failure needs a team operator before anyone can request again."}
          </p>
        )}
        {allowsNewRequest(fixture.registration_request_status, job.data) && !eligibility.ok && (
          <p className="mt-1 text-sm text-neutral-400">{eligibility.reason}</p>
        )}
        <RegistrationRequest fixture={fixture} job={job.data} nowMs={now * 1000} />
        <button
          type="button"
          disabled
          title="Needs the M4 contract"
          className="mt-3 w-full rounded bg-neutral-800 px-3 py-2 text-sm text-neutral-500"
        >
          {canCreateMarket(fixture.registration_request_status) ? "Create market" : "Create market (after registration)"}
        </button>
        <p className="mt-1 text-xs text-neutral-500">Market creation is enabled once the M4 contract is deployed.</p>
      </div>

      <ResultHistory fixture={fixture} results={results} failed={resultsFailed} />
    </div>
  );
}

function OutcomeTile({ label, team, accent }: { label: string; team: string; accent: string }) {
  return (
    <div className="rounded-md border border-neutral-800 bg-neutral-950 p-3">
      <p className={`text-xs font-semibold ${accent}`}>{label}</p>
      <p className="mt-1 text-neutral-100">{team} wins</p>
    </div>
  );
}

function Evidence({ url, hash }: { url: string | null; hash: string | null }) {
  if (!url || !hash) return <p className="mt-1 text-xs text-red-300">No organizer evidence recorded.</p>;
  return (
    <p className="mt-1 text-xs text-neutral-500">
      Evidence:{" "}
      <a href={url} target="_blank" rel="noreferrer" className="text-amber-300 underline underline-offset-2">
        organizer page
      </a>{" "}
      <span className="font-mono" title={hash}>
        ({shortenAddress(hash)})
      </span>
    </p>
  );
}

function ResultHistory({
  fixture,
  results,
  failed,
}: {
  fixture: Fixture;
  results: ResultObservation[] | undefined;
  failed: boolean;
}) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Source results</p>
      <p className="mt-1 text-xs text-neutral-500">
        Imported observations, oldest first. They help the proposer but do not settle the market.
      </p>
      {failed && <p className="mt-2 text-sm text-red-400">Results unavailable right now.</p>}
      {results && results.length === 0 && <p className="mt-2 text-sm text-neutral-400">No result recorded yet.</p>}
      {results && results.length > 0 && (
        <ul className="mt-2 flex flex-col gap-1 text-sm">
          {results.map((r) => (
            <li key={r.id} className="flex flex-wrap items-center gap-2 text-neutral-300">
              <Badge tone={matchStatusTone(r.match_status)}>{MATCH_STATUS_LABELS[r.match_status]}</Badge>
              {winnerName(fixture, r.winner_team_id) && <span>Winner: {winnerName(fixture, r.winner_team_id)}</span>}
              <span className="text-xs text-neutral-500">{new Date(r.source_updated_at).toLocaleString()}</span>
              <a href={r.evidence_url} target="_blank" rel="noreferrer" className="text-xs text-amber-300 underline underline-offset-2">
                evidence
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
