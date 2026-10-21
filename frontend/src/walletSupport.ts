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

// wagmi auto-adds a connector for each wallet extension that announces itself
// (EIP-6963), e.g. "MetaMask". Hide the generic injected fallback when a named
// one exists so the same wallet is not offered twice.
export function visibleConnectors<T extends ConnectorInfo>(connectors: readonly T[]): T[] {
  const hasDiscoveredWallet = connectors.some((c) => c.type === "injected" && c.id !== "injected");
  return connectors.filter((c) => !(hasDiscoveredWallet && c.id === "injected"));
}

// Coinbase Smart Wallet supports Base Sepolia but not Ethereum Sepolia for
// transactions: it connects and reads, but claim/approve/buy fail with
// "Sepolia is not supported". MetaMask works on Ethereum Sepolia.
export function smartWalletCannotTransact(chainMode: ChainMode, connectorId: string | undefined): boolean {
  return chainMode === "sepolia" && connectorId === COINBASE_CONNECTOR_ID;
}

export const SEPOLIA_SMART_WALLET_NOTE =
  "On Ethereum Sepolia, Coinbase Smart Wallet can connect and read but cannot send transactions. To claim ACON or trade, connect MetaMask instead.";
