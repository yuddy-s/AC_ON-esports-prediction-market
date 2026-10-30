import { NETWORK_LABEL } from "./config";
import { FixtureCatalog } from "./FixtureCatalog";
import { FixtureDetail } from "./FixtureDetail";
import { Header } from "./Header";
import { MarketPage } from "./MarketPage";
import { MarketsPage } from "./MarketsPage";
import { useRoute, type Route } from "./router";
import { Dots } from "./ui";

export default function App() {
  const route = useRoute();

  return (
    <div className="flex min-h-screen flex-col">
      <Header route={route} />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        <Page route={route} />
      </main>
      <footer className="border-t border-bronze/40">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-4 font-mono text-[11px] text-dust sm:px-6">
          <span>AC_ON · ESPORTS PREDICTION MARKET · {NETWORK_LABEL.toUpperCase()}</span>
          <span className="flex items-center gap-2">
            TEST TOKENS ONLY · NO REAL MONEY <Dots size="h-1.5 w-1.5" />
          </span>
        </div>
      </footer>
    </div>
  );
}

function Page({ route }: { route: Route }) {
  switch (route.page) {
    case "markets":
      return <MarketsPage />;
    case "market":
      return <MarketPage id={route.id} />;
    case "fixtures":
      return <FixtureCatalog />;
    case "fixture":
      return <FixtureDetail id={route.id} />;
    case "not-found":
      return (
        <p className="text-sand">
          Page not found. <a href="#/" className="link">Go to markets</a>
        </p>
      );
  }
}
