import { WalletConnect } from "./WalletConnect";
import { MarketCard } from "./MarketCard";

export default function App() {
  return (
    <div className="min-h-screen bg-neutral-950 px-6 py-16">
      <div className="mx-auto max-w-lg">
        <h1 className="text-2xl font-bold text-amber-300">
          Esports Prediction Market
        </h1>
        <p className="mt-1 text-sm text-neutral-400">
          Team AC_ON — Milestone 2 prototype
        </p>

        <div className="mt-8">
          <WalletConnect />
        </div>

        <div className="mt-6">
          <MarketCard />
        </div>
      </div>
    </div>
  );
}
