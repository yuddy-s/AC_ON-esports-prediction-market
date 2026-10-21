import { http, createConfig, type CreateConnectorFn } from "wagmi";
import { foundry, sepolia } from "wagmi/chains";
import { coinbaseWallet, injected, mock } from "wagmi/connectors";
import { CHAIN, CHAIN_MODE } from "./config";

// Anvil's default test account #0 (public, same on every Anvil instance).
// Anvil holds its key and signs for it, so no private key is in the frontend.
// It is the deployer in contracts/script/Deploy.s.sol, so it already has ACON.
const ANVIL_ACCOUNT_0 = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266";

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
  connectors.push(mock({ accounts: [ANVIL_ACCOUNT_0] }));
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
