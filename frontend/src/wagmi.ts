import { http, createConfig, type CreateConnectorFn } from "wagmi";
import { foundry, sepolia } from "wagmi/chains";
import { coinbaseWallet, injected, mock } from "wagmi/connectors";
import { ANVIL_ACCOUNT, CHAIN, CHAIN_MODE } from "./config";

const connectors: CreateConnectorFn[] = [
  // Primary: no extension or app install needed, works on any computer
  // (passkey / email login via a popup). This is what most users and
  // demo machines should use. Only works on public networks (Sepolia).
  coinbaseWallet({
    appName: "Esports Prediction Market",
    preference: "smartWalletOnly",
  }),
  // Fallback: for users who already have MetaMask or another extension.
  injected(),
];

if (CHAIN_MODE === "anvil") {
  // Local development only: Coinbase Smart Wallet cannot reach a local chain.
  // Anvil's default test accounts are unlocked, so Anvil signs for them and
  // no private key is in the frontend.
  connectors.push(mock({ accounts: [ANVIL_ACCOUNT] }));
}

export const config = createConfig({
  chains: [CHAIN],
  connectors,
  // CHAIN is one of these two; listing both keeps the transport map typed.
  transports: {
    [sepolia.id]: http(),
    [foundry.id]: http(),
  },
});

declare module "wagmi" {
  interface Register {
    config: typeof config;
  }
}
