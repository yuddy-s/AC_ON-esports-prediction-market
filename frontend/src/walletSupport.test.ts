import { describe, expect, it } from "vitest";
import { connectorLabel, smartWalletCannotTransact, visibleConnectors } from "./walletSupport";

describe("connectorLabel", () => {
  it("names the generic injected connector MetaMask", () => {
    expect(connectorLabel({ id: "injected", name: "Injected", type: "injected" })).toBe("MetaMask (browser wallet)");
  });

  it("marks the Anvil test wallet as local only", () => {
    expect(connectorLabel({ id: "mock", name: "Mock Connector", type: "mock" })).toBe("Anvil test wallet (local only)");
  });

  it("keeps the name of wallets discovered by the browser", () => {
    expect(connectorLabel({ id: "io.rabby", name: "Rabby Wallet", type: "injected" })).toBe("Rabby Wallet");
  });
});

describe("smartWalletCannotTransact", () => {
  it("warns only for Coinbase Smart Wallet on Ethereum Sepolia", () => {
    expect(smartWalletCannotTransact("sepolia", "coinbaseWalletSDK")).toBe(true);
    expect(smartWalletCannotTransact("sepolia", "injected")).toBe(false);
    expect(smartWalletCannotTransact("anvil", "coinbaseWalletSDK")).toBe(false);
    expect(smartWalletCannotTransact("sepolia", undefined)).toBe(false);
  });
});

describe("visibleConnectors", () => {
  const coinbase = { id: "coinbaseWalletSDK", name: "Coinbase Wallet", type: "coinbaseWallet" };
  const generic = { id: "injected", name: "Injected", type: "injected" };
  const metamask = { id: "io.metamask", name: "MetaMask", type: "injected" };

  it("hides the generic browser-wallet button when MetaMask is detected", () => {
    expect(visibleConnectors([coinbase, generic, metamask]).map((c) => c.id)).toEqual(["coinbaseWalletSDK", "io.metamask"]);
  });

  it("keeps the generic button as a fallback when no wallet is detected", () => {
    expect(visibleConnectors([coinbase, generic]).map((c) => c.id)).toEqual(["coinbaseWalletSDK", "injected"]);
  });
});
