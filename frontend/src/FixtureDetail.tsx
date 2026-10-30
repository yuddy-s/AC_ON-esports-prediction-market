import { useQuery } from "@tanstack/react-query";
import { API_URL, FIXTURE_SOURCE } from "./config";
import { Badge } from "./Badge";
import { SourceNote } from "./FixtureCatalog";
import { fetchFixture, fetchFixtureResults, type Fixture, type ResultObservation } from "./fixturesApi";
import {
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
import { Panel, PanelTitle, Tag } from "./ui";
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
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <a href="#/fixtures" className="font-display text-xs font-semibold uppercase tracking-wider text-sand hover:text-gold">
          ← All fixtures
        </a>
        <SourceNote />
      </div>

      {fixture.isLoading && <p className="text-sand">Loading fixture…</p>}
      {fixture.isError && <p className="text-signal">Fixture catalog unavailable at {API_URL}.</p>}
      {fixture.data === null && <p className="text-sand">Fixture #{id} was not found.</p>}
      {fixture.data && <FixtureBody fixture={fixture.data} results={results.data} resultsFailed={results.isError} />}
    </div>
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
  const eligibility = registrationEligibility(fixture, now * 1000);

  return (
    <>
      <Matchup fixture={fixture} />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex flex-col gap-6">
          <Panel>
            <PanelTitle tag="Rules" title="Source and resolution" />
            <p className="mt-3 text-cream">
              The market resolves <span className="font-semibold text-gold">YES</span> if {teams.yes} wins and{" "}
              <span className="font-semibold text-signal-soft">NO</span> if {teams.no} wins. A canceled, tied, no-contest or
              unsupported result is proposed as VOID. A proposed result can be challenged.
            </p>
            <div className="mt-4 flex flex-col gap-1 border-t border-bronze/40 pt-3 text-sm text-sand">
              <span>
                Provider <span className="font-mono text-paper">{fixture.provider_id}</span> · match{" "}
                <span className="font-mono text-paper">{fixture.external_match_id}</span>
              </span>
              <Evidence url={fixture.evidence_url} hash={fixture.evidence_hash} />
            </div>
          </Panel>
          <ResultHistory fixture={fixture} results={results} failed={resultsFailed} />
        </div>

        <section className="hud flex flex-col gap-3 border-t-2 border-gold bg-ink-600 p-5 lg:sticky lg:top-24">
          <div className="flex items-center justify-between gap-2">
            <Tag tone="gold">On-chain</Tag>
            <Badge tone={registration.tone}>{registration.label}</Badge>
          </div>
          <h2 className="font-display text-lg font-semibold uppercase tracking-wide text-paper">Registration</h2>
          <p className="text-sm text-cream">{registration.detail}</p>
          {fixture.registration_request_status === null && !eligibility.ok && (
            <p className="text-sm text-sand">{eligibility.reason}</p>
          )}
          <RegistrationRequest fixture={fixture} nowMs={now * 1000} />
          <div className="border-t border-bronze/40 pt-3">
            <button type="button" disabled title="Needs the M4 contract" className="btn-gold w-full">
              {canCreateMarket(fixture.registration_request_status) ? "Create market" : "Create market · after registration"}
            </button>
            <p className="mt-1.5 text-xs text-dust">Market creation is enabled once the M4 contract is deployed.</p>
          </div>
        </section>
      </div>
    </>
  );
}

function Matchup({ fixture }: { fixture: Fixture }) {
  return (
    <div className="hud overflow-hidden bg-ink-900">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-bronze/50 px-5 py-2">
        <span className="font-mono text-[11px] uppercase text-dust">
          {gameLabel(fixture.game_id)} · FIX-{String(fixture.id).padStart(3, "0")}
        </span>
        <Badge tone={matchStatusTone(fixture.match_status)}>{MATCH_STATUS_LABELS[fixture.match_status]}</Badge>
      </div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-5 py-6">
        <TeamSide name={fixture.team_a_name} outcome="YES" align="left" color="text-gold" />
        <div className="flex flex-col items-center px-2">
          <span className="font-display text-xl font-bold text-dust">VS</span>
          <span className="num mt-1 text-center font-mono text-xs text-sand">
            {new Date(fixture.scheduled_start).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}
          </span>
        </div>
        <TeamSide name={fixture.team_b_name} outcome="NO" align="right" color="text-signal-soft" />
      </div>
      <div className="flex h-1.5">
        <div className="flex-1 bg-gold" />
        <div className="w-0.5 bg-ink-900" />
        <div className="flex-1 bg-signal-soft" />
      </div>
    </div>
  );
}

function TeamSide({ name, outcome, align, color }: { name: string; outcome: string; align: "left" | "right"; color: string }) {
  return (
    <div className={`flex min-w-0 flex-col ${align === "right" ? "items-end text-right" : "items-start"}`}>
      <span className={`font-display text-xs font-bold tracking-[0.2em] ${color}`}>{outcome}</span>
      <span className="break-words font-display text-2xl font-bold uppercase leading-tight text-paper sm:text-4xl">{name}</span>
    </div>
  );
}

function Evidence({ url, hash }: { url: string | null; hash: string | null }) {
  if (!url || !hash) return <span className="text-signal">No organizer evidence recorded.</span>;
  return (
    <span>
      Evidence{" "}
      <a href={url} target="_blank" rel="noreferrer" className="link">
        organizer page
      </a>{" "}
      <span className="font-mono text-xs text-dust" title={hash}>
        {shortenAddress(hash)}
      </span>
    </span>
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
    <Panel>
      <PanelTitle tag="Source" title="Results" />
      <p className="mt-2 text-xs text-dust">Imported observations, oldest first. They help the proposer but do not settle the market.</p>
      {failed && <p className="mt-3 text-sm text-signal">Results unavailable right now.</p>}
      {results && results.length === 0 && <p className="mt-3 text-sm text-sand">No result recorded yet.</p>}
      {results && results.length > 0 && (
        <ul className="mt-3 flex flex-col">
          {results.map((r) => (
            <li key={r.id} className="flex flex-wrap items-center gap-3 border-t border-bronze/30 py-2 text-sm">
              <Badge tone={matchStatusTone(r.match_status)}>{MATCH_STATUS_LABELS[r.match_status]}</Badge>
              {winnerName(fixture, r.winner_team_id) && (
                <span className="text-paper">
                  Winner <span className="font-semibold">{winnerName(fixture, r.winner_team_id)}</span>
                </span>
              )}
              <span className="num font-mono text-xs text-dust">{new Date(r.source_updated_at).toLocaleString()}</span>
              <a href={r.evidence_url} target="_blank" rel="noreferrer" className="link text-xs">
                evidence
              </a>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}
