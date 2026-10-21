import type { ChainMode } from "./config";

interface ConnectorInfo {
  id: string;
  name: string;
  type: string;
}

const COINBASE_CONNECTOR_ID = "coinbaseWalletSDK";

// Button label for a secondary wallet option.
export function connectorLabel(connector: ConnectorInfo): string {
  if (connector.type === "mock") return "Anvil test wallet (local only)";
  if (connector.id === "injected") return "MetaMask (browser wallet)";
  return connector.name;
}

// Coinbase Smart Wallet supports Base Sepolia but not Ethereum Sepolia for
// transactions: it connects and reads, but claim/approve/buy fail with
// "Sepolia is not supported". MetaMask works on Ethereum Sepolia.
export function smartWalletCannotTransact(chainMode: ChainMode, connectorId: string | undefined): boolean {
  return chainMode === "sepolia" && connectorId === COINBASE_CONNECTOR_ID;
}

export const SEPOLIA_SMART_WALLET_NOTE =
  "On Ethereum Sepolia, Coinbase Smart Wallet can connect and read but cannot send transactions. To claim ACON or trade, connect MetaMask instead.";
