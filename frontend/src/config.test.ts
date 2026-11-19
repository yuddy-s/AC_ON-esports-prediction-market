import { describe, expect, it } from "vitest";
import { PUBLIC_SEPOLIA_RPCS, sepoliaRpcUrls } from "./config";

describe("sepoliaRpcUrls (FE-B2)", () => {
  it("uses the keyless public endpoints when no custom URL is set", () => {
    expect(sepoliaRpcUrls(undefined)).toEqual([...PUBLIC_SEPOLIA_RPCS]);
    expect(sepoliaRpcUrls("  ")).toEqual([...PUBLIC_SEPOLIA_RPCS]);
  });

  it("tries a custom URL first and keeps the public fallbacks", () => {
    expect(sepoliaRpcUrls("https://rpc.example.org")).toEqual(["https://rpc.example.org", ...PUBLIC_SEPOLIA_RPCS]);
  });

  it("does not list the same endpoint twice", () => {
    expect(sepoliaRpcUrls(PUBLIC_SEPOLIA_RPCS[1])).toEqual([PUBLIC_SEPOLIA_RPCS[1], PUBLIC_SEPOLIA_RPCS[0]]);
  });

  it("rejects a non-https URL", () => {
    expect(() => sepoliaRpcUrls("http://rpc.example.org")).toThrow(/https/);
  });
});
