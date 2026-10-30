import { getAddress, type Address } from "viem";
import { foundry, sepolia } from "wagmi/chains";

// All deployment-specific values come from Vite env vars (VITE_* only, so no
// server secrets ever reach the browser). See frontend/.env.example.

export type ChainMode = "anvil" | "sepolia";

function readChainMode(value: string | undefined): ChainMode {
  if (value === undefined || value === "" || value === "sepolia") return "sepolia";
  if (value === "anvil") return "anvil";
  throw new Error(`VITE_CHAIN must be "anvil" or "sepolia", got "${value}"`);
}

function readAddress(name: string, value: string | undefined): Address | undefined {
  if (!value) return undefined;
  try {
    return getAddress(value);
  } catch {
    throw new Error(`${name} is not a valid address: "${value}"`);
  }
}

export const CHAIN_MODE = readChainMode(import.meta.env.VITE_CHAIN);

// anvil = local Foundry chain (31337) for development; sepolia = the real demo.
export const CHAIN = CHAIN_MODE === "anvil" ? foundry : sepolia;

export const PREDICTION_MARKET_ADDRESS = readAddress(
  "VITE_PREDICTION_MARKET_ADDRESS",
  import.meta.env.VITE_PREDICTION_MARKET_ADDRESS,
);

export const ACON_TOKEN_ADDRESS = readAddress(
  "VITE_ACON_TOKEN_ADDRESS",
  import.meta.env.VITE_ACON_TOKEN_ADDRESS,
);

// Which Anvil test account the local-only test wallet uses (default: #0, the
// deployer). Set another default Anvil address to test the faucet claim.
export const ANVIL_ACCOUNT =
  readAddress("VITE_ANVIL_ACCOUNT", import.meta.env.VITE_ANVIL_ACCOUNT) ??
  getAddress("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266");

export const DEMO_MARKET_ID = BigInt(import.meta.env.VITE_DEMO_MARKET_ID ?? "0");

// FastAPI backend (indexed markets/trades). Optional until the indexer runs.
export const API_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/+$/, "");

// Where the fixture catalog comes from: "api" (backend /api/fixtures) or
// "mock" (fictional fixtures bundled with the frontend, no backend needed).
// Defaults to the API when VITE_API_URL is set.
export type FixtureSource = "api" | "mock";

function readFixtureSource(value: string | undefined): FixtureSource {
  if (value === undefined || value === "") return API_URL ? "api" : "mock";
  if (value === "api" || value === "mock") return value;
  throw new Error(`VITE_FIXTURE_SOURCE must be "api" or "mock", got "${value}"`);
}

export const FIXTURE_SOURCE = readFixtureSource(import.meta.env.VITE_FIXTURE_SOURCE);

export const EXPLORER_URL = CHAIN.blockExplorers?.default.url;
