import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { API_URL, FIXTURE_SOURCE } from "./config";
import { Badge } from "./Badge";
import { fetchFixtures, type Fixture } from "./fixturesApi";
import { describeRegistration, gameLabel, MATCH_STATUS_LABELS, matchStatusTone } from "./fixtureStatus";
import { fixtureHref } from "./router";
import { Tag } from "./ui";

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
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-bronze/50 pb-5">
        <div className="flex flex-col items-start gap-2">
          <Tag>Fixtures</Tag>
          <h1 className="font-display text-3xl font-bold uppercase tracking-wide text-paper sm:text-4xl">Match schedule</h1>
          <p className="max-w-xl text-sand">
            Imported match data. A fixture is not a market: it has to be registered on-chain before anyone can create one.
          </p>
        </div>
        <SourceNote />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {(["upcoming", "finished", "all"] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatus(s)}
            className={`border px-3 py-1 font-display text-xs font-semibold uppercase tracking-wider ${
              status === s ? "border-gold bg-gold text-ink-900" : "border-bronze text-sand hover:border-gold hover:text-gold"
            }`}
          >
            {s}
          </button>
        ))}
        <select
          value={game}
          onChange={(e) => setGame(e.target.value)}
          aria-label="Filter by game"
          className="border border-bronze bg-ink-900 px-2 py-1 font-display text-xs uppercase tracking-wider text-cream"
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
        <p className="text-signal">VITE_API_URL is not set, so the fixture catalog cannot load.</p>
      )}
      {fixtures.isLoading && <p className="text-sand">Loading fixtures…</p>}
      {fixtures.isError && (
        <p className="text-signal">Fixture catalog unavailable at {API_URL}. Markets already on the chain are unaffected.</p>
      )}
      {fixtures.data && shown.length === 0 && <p className="text-sand">No fixtures match this filter.</p>}

      <ul className="flex flex-col gap-2">
        {shown.map((f) => (
          <FixtureRow key={f.id} fixture={f} />
        ))}
      </ul>
    </div>
  );
}

function FixtureRow({ fixture }: { fixture: Fixture }) {
  const registration = describeRegistration(fixture.registration_request_status);
  const start = new Date(fixture.scheduled_start);
  return (
    <li>
      <a
        href={fixtureHref(fixture.id)}
        className="hud-sm group grid grid-cols-[84px_1fr] items-center gap-4 border-l-2 border-bronze bg-ink-700 px-4 py-3 hover:border-gold hover:bg-ink-600 sm:grid-cols-[96px_1fr_auto]"
      >
        <div className="flex flex-col border-r border-bronze/40 pr-3 font-mono">
          <span className="text-xs uppercase text-sand">{start.toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>
          <span className="num whitespace-nowrap text-base text-paper">{start.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}</span>
        </div>
        <div className="min-w-0">
          <p className="label">{gameLabel(fixture.game_id)}</p>
          <p className="truncate font-display text-lg font-semibold text-paper group-hover:text-gold">
            <span className="text-gold">{fixture.team_a_name}</span>
            <span className="mx-2 text-sm text-dust">VS</span>
            <span className="text-signal-soft">{fixture.team_b_name}</span>
          </p>
        </div>
        <div className="col-span-2 flex flex-wrap gap-2 sm:col-span-1 sm:justify-end">
          <Badge tone={matchStatusTone(fixture.match_status)}>{MATCH_STATUS_LABELS[fixture.match_status]}</Badge>
          <Badge tone={registration.tone}>{registration.label}</Badge>
        </div>
      </a>
    </li>
  );
}

export function SourceNote() {
  return FIXTURE_SOURCE === "mock" ? (
    <span className="border border-gold/60 px-2 py-1 font-mono text-[11px] text-gold">MOCK FIXTURES · FICTIONAL, NOT FROM THE BACKEND</span>
  ) : (
    <span className="font-mono text-[11px] text-dust">FROM THE FIXTURE API</span>
  );
}
