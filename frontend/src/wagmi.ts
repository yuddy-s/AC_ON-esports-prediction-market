import { http, createConfig } from "wagmi";
import { sepolia } from "wagmi/chains";
import { coinbaseWallet, injected } from "wagmi/connectors";

// The Milestone 2 PredictionMarket deployment is on Ethereum Sepolia.
export const config = createConfig({
  chains: [sepolia],
  connectors: [
    // Primary: no extension or app install needed, works on any computer
    // (passkey / email login via a popup). This is what most users and
    // demo machines should use.
    coinbaseWallet({
      appName: "Esports Prediction Market",
      preference: "smartWalletOnly",
    }),
    // Fallback: for users who already have MetaMask or another extension.
    injected(),
  ],
  transports: {
    [sepolia.id]: http(),
  },
});

declare module "wagmi" {
  interface Register {
    config: typeof config;
  }
}
