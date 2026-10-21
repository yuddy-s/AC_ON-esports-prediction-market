import { describe, expect, it } from "vitest";
import { connectorLabel, smartWalletCannotTransact } from "./walletSupport";

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
