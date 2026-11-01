import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { API_URL, FIXTURE_SOURCE } from "./config";
import { Badge } from "./Badge";
import { fetchFixtures, type Fixture } from "./fixturesApi";
import { describeRegistration, gameLabel, MATCH_STATUS_LABELS, matchStatusTone } from "./fixtureStatus";
import { fixtureHref } from "./router";

type StatusFilter = "upcoming" | "finished" | "all";

const UPCOMING = new Set(["scheduled", "live", "postponed"]);

function matchesFilter(fixture: Fixture, status: StatusFilter, game: string): boolean {
  if (game !== "all" && fixture.game_id !== game) return false;
  if (status === "upcoming") return UPCOMING.has(fixture.match_status);
  if (status === "finished") return !UPCOMING.has(fixture.match_status);
  return true;
}

export function FixtureCatalog() {
  const [status, setStatus] = useState<StatusFilter>("upcoming");
  const [game, setGame] = useState("all");
  const fixtures = useQuery({
    queryKey: ["fixtures", FIXTURE_SOURCE],
    queryFn: ({ signal }) => fetchFixtures(signal),
    enabled: FIXTURE_SOURCE === "mock" || API_URL !== "",
    refetchInterval: 30_000,
  });

  const items = fixtures.data?.items ?? [];
  const games = useMemo(() => [...new Set(items.map((f) => f.game_id))].sort(), [items]);
  const shown = items.filter((f) => matchesFilter(f, status, game));

  return (
    <section className="rounded-lg border border-neutral-700 bg-neutral-900 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-400">Fixture catalog</h2>
        <SourceNote />
      </div>
      <p className="mt-1 text-xs text-neutral-500">
        Imported match data. A fixture is not a market: it has to be registered on-chain before anyone can create one.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {(["upcoming", "finished", "all"] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatus(s)}
            className={`rounded px-3 py-1 text-xs capitalize ${
              status === s ? "bg-amber-300 text-neutral-950" : "bg-neutral-800 text-neutral-300 hover:bg-neutral-700"
            }`}
          >
            {s}
          </button>
        ))}
        <select
          value={game}
          onChange={(e) => setGame(e.target.value)}
          aria-label="Filter by game"
          className="rounded bg-neutral-800 px-2 py-1 text-xs text-neutral-200"
        >
          <option value="all">All games</option>
          {games.map((g) => (
            <option key={g} value={g}>
              {gameLabel(g)}
            </option>
          ))}
        </select>
      </div>

      {FIXTURE_SOURCE === "api" && !API_URL && (
        <p className="mt-4 text-sm text-red-400">VITE_API_URL is not set, so the fixture catalog cannot load.</p>
      )}
      {fixtures.isLoading && <p className="mt-4 text-sm text-neutral-400">Loading fixtures…</p>}
      {fixtures.isError && (
        <p className="mt-4 text-sm text-red-400">
          Fixture catalog unavailable at {API_URL}. Markets already on the chain are unaffected.
        </p>
      )}
      {fixtures.data && shown.length === 0 && <p className="mt-4 text-sm text-neutral-400">No fixtures match this filter.</p>}

      <ul className="mt-4 flex flex-col gap-2">
        {shown.map((f) => (
          <FixtureRow key={f.id} fixture={f} />
        ))}
      </ul>
    </section>
  );
}

function FixtureRow({ fixture }: { fixture: Fixture }) {
  const registration = describeRegistration(fixture.registration_request_status);
  return (
    <li>
      <a
        href={fixtureHref(fixture.id)}
        className="block rounded-md border border-neutral-800 bg-neutral-950 p-3 hover:border-amber-300/60"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-semibold text-neutral-100">
            {fixture.team_a_name} <span className="text-neutral-500">vs</span> {fixture.team_b_name}
          </p>
          <span className="text-xs text-neutral-500">{gameLabel(fixture.game_id)}</span>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Badge tone={matchStatusTone(fixture.match_status)}>{MATCH_STATUS_LABELS[fixture.match_status]}</Badge>
          <Badge tone={registration.tone}>{registration.label}</Badge>
          <span className="text-xs text-neutral-400">{new Date(fixture.scheduled_start).toLocaleString()}</span>
        </div>
      </a>
    </li>
  );
}

export function SourceNote() {
  return FIXTURE_SOURCE === "mock" ? (
    <span className="text-xs text-amber-300">Mock fixtures (fictional, not from the backend)</span>
  ) : (
    <span className="text-xs text-neutral-500">from the fixture API</span>
  );
}
