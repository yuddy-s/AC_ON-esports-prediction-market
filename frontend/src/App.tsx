import { WalletConnect } from "./WalletConnect";
import { MarketCard } from "./MarketCard";
import { AconPanel } from "./AconPanel";
import { TradePanel } from "./TradePanel";
import { RecentTrades } from "./RecentTrades";
import { FixtureCatalog } from "./FixtureCatalog";
import { FixtureDetail } from "./FixtureDetail";
import { useRoute, type Route } from "./router";

const NAV = [
  { href: "#/", label: "Markets", pages: ["markets"] },
  { href: "#/fixtures", label: "Fixtures", pages: ["fixtures", "fixture"] },
] as const;

export default function App() {
  const route = useRoute();

  return (
    <div className="min-h-screen bg-neutral-950 px-4 py-12 sm:px-6">
      <div className="mx-auto max-w-lg">
        <h1 className="text-2xl font-bold text-amber-300">
          Esports Prediction Market
        </h1>
        <p className="mt-1 text-sm text-neutral-400">
          Team AC_ON — Milestone 4
        </p>

        <nav className="mt-6 flex gap-2">
          {NAV.map((item) => {
            const active = (item.pages as readonly string[]).includes(route.page);
            return (
              <a
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`rounded px-3 py-1.5 text-sm ${
                  active ? "bg-amber-300 font-semibold text-neutral-950" : "bg-neutral-900 text-neutral-300 hover:bg-neutral-800"
                }`}
              >
                {item.label}
              </a>
            );
          })}
        </nav>

        <div className="mt-6">
          <WalletConnect />
        </div>

        <Page route={route} />
      </div>
    </div>
  );
}

function Page({ route }: { route: Route }) {
  switch (route.page) {
    case "markets":
      return (
        <>
          <div className="mt-6">
            <AconPanel />
          </div>
          <div className="mt-6">
            <MarketCard />
          </div>
          <div className="mt-6">
            <TradePanel />
          </div>
          <div className="mt-6">
            <RecentTrades />
          </div>
        </>
      );
    case "fixtures":
      return (
        <div className="mt-6">
          <FixtureCatalog />
        </div>
      );
    case "fixture":
      return (
        <div className="mt-6">
          <FixtureDetail id={route.id} />
        </div>
      );
    case "not-found":
      return (
        <p className="mt-6 text-sm text-neutral-400">
          Page not found. <a href="#/" className="text-amber-300 underline underline-offset-2">Go to markets</a>
        </p>
      );
  }
}
