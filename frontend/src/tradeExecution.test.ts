import { beforeEach, describe, expect, it, vi } from "vitest";
import { UserRejectedRequestError, type Hash } from "viem";
import { executeTrade, type TradeRequest } from "./tradeExecution";
import { predictionMarketAbi } from "./predictionMarket";
import { CHAIN } from "./config";
import type { TradeStatus } from "./tradeStatus";

const rpc = vi.hoisted(() => ({
  lagLatest: false,
  missingApprovalBlock: false,
  allProvidersMissing: false,
  contractError: "" as "" | "SlippageExceeded" | "InsufficientTokenAllowance",
  calls: [] as { provider: string; method: string; params: readonly unknown[] }[],
  write: vi.fn(),
  wait: vi.fn(),
}));

vi.mock("./config", async (original) => ({
  ...(await original<typeof import("./config")>()),
  API_URL: "",
}));

// Real wagmi/viem simulation and fallback transport, with two local RPC stubs.
// Wallet submission and receipts are mocked: these tests never sign or send.
vi.mock("./wagmi", async () => {
  const { createConfig } = await import("wagmi");
  const { custom, fallback } = await import("viem");
  const { CHAIN } = await import("./config");
  const { predictionMarketAbi } = await import("./predictionMarket");
  const { encodeErrorResult, encodeFunctionResult } = await import("viem");
  const transport = (provider: string) => custom({
    async request({ method, params }) {
      rpc.calls.push({ provider, method, params: params as readonly unknown[] });
      if (method !== "eth_call") throw new Error(`Unexpected RPC method: ${method}`);
      const [call, block] = params as [{ data: string }, string];
      if (block !== "latest" && (rpc.allProvidersMissing || (rpc.missingApprovalBlock && provider === "behind"))) {
        throw Object.assign(new Error("header not found"), { code: -32000 });
      }
      const stale = rpc.lagLatest && block === "latest";
      if (stale || rpc.contractError) {
        const data = rpc.contractError === "SlippageExceeded"
          ? encodeErrorResult({ abi: predictionMarketAbi, errorName: "SlippageExceeded", args: [6n * ONE, 5n * ONE] })
          : encodeErrorResult({ abi: predictionMarketAbi, errorName: "InsufficientTokenAllowance", args: [5n * ONE, 0n] });
        throw Object.assign(new Error("execution reverted"), { code: 3, data });
      }
      const functionName = call.data.startsWith("0x9b29429d") ? "buy" : "sell";
      return encodeFunctionResult({ abi: predictionMarketAbi, functionName, result: 5n * ONE });
    },
  }, { retryCount: 0 });
  return { config: createConfig({
    chains: [CHAIN],
    connectors: [],
    transports: {
      11155111: fallback([transport("behind"), transport("current")], { retryCount: 0 }),
      31337: fallback([transport("behind"), transport("current")], { retryCount: 0 }),
    },
  }) };
});

vi.mock("wagmi/actions", async (original) => ({
  ...(await original<typeof import("wagmi/actions")>()),
  writeContract: rpc.write,
  waitForTransactionReceipt: rpc.wait,
}));

const ONE = 10n ** 18n;
const ACCOUNT = "0x1111111111111111111111111111111111111111";
const MARKET = "0x2222222222222222222222222222222222222222";
const TOKEN = "0x3333333333333333333333333333333333333333";
const APPROVAL = `0x${"aa".repeat(32)}` as Hash;
const TRADE = `0x${"bb".repeat(32)}` as Hash;
const APPROVAL_BLOCK = 123n;
const buy: Extract<TradeRequest, { side: "buy" }> = {
  account: ACCOUNT, market: MARKET, marketId: 1n, outcome: 0, shares: 10n * ONE,
  side: "buy", token: TOKEN, maxCost: 5n * ONE, needsApproval: true,
};

function run(request: TradeRequest = buy) {
  const states: TradeStatus[] = [];
  const refresh = vi.fn();
  const done = executeTrade(request, (status) => states.push(status), refresh);
  return { states, refresh, done };
}

describe("FE-B3: approve then buy across RPC views", () => {
  beforeEach(() => {
    rpc.calls = [];
    rpc.lagLatest = false;
    rpc.missingApprovalBlock = false;
    rpc.allProvidersMissing = false;
    rpc.contractError = "";
    rpc.write.mockReset().mockResolvedValueOnce(APPROVAL).mockResolvedValue(TRADE);
    rpc.wait.mockReset()
      .mockResolvedValueOnce({ status: "success", blockNumber: APPROVAL_BLOCK })
      .mockResolvedValue({ status: "success", blockNumber: 124n });
  });

  it("buys without refresh when latest would still report zero allowance", async () => {
    rpc.lagLatest = true;
    const { states, refresh, done } = run();
    await done;
    expect(states[states.length - 1]).toMatchObject({ kind: "mined", hash: TRADE });
    expect(rpc.calls.map((call) => call.params[1])).toEqual(["0x7b"]);
    expect(rpc.write).toHaveBeenCalledTimes(2);
    expect(rpc.write.mock.calls[0][1]).toMatchObject({
      address: TOKEN, functionName: "approve", args: [MARKET, buy.maxCost], chainId: CHAIN.id,
    });
    expect(rpc.write.mock.calls[1][1]).toMatchObject({
      address: MARKET, functionName: "buy", args: [1n, 0, 10n * ONE, buy.maxCost], chainId: CHAIN.id,
    });
    expect(rpc.write.mock.calls[1][1]).not.toHaveProperty("blockNumber");
    expect(refresh).toHaveBeenCalledTimes(2);
  });

  it("falls back when an RPC cannot yet serve the approval block", async () => {
    rpc.missingApprovalBlock = true;
    const { states, done } = run();
    await done;
    expect(states[states.length - 1]).toMatchObject({ kind: "mined" });
    expect(rpc.calls.map((call) => [call.provider, call.params[1]])).toEqual([
      ["behind", "0x7b"], ["current", "0x7b"],
    ]);
    expect(rpc.write).toHaveBeenCalledTimes(2);
  });

  it("does not simulate or request the buy before approval is mined", async () => {
    let mined!: (value: { status: string; blockNumber: bigint }) => void;
    rpc.wait.mockReset().mockReturnValueOnce(new Promise((resolve) => { mined = resolve; }))
      .mockResolvedValue({ status: "success", blockNumber: 124n });
    const { done } = run();
    await vi.waitFor(() => expect(rpc.wait).toHaveBeenCalledTimes(1));
    expect(rpc.calls).toEqual([]);
    expect(rpc.write).toHaveBeenCalledTimes(1);
    mined({ status: "success", blockNumber: APPROVAL_BLOCK });
    await done;
    expect(rpc.calls[0].params[1]).toBe("0x7b");
  });

  it("does not submit a buy if no RPC can serve the approval block", async () => {
    rpc.allProvidersMissing = true;
    const { states, refresh, done } = run();
    await done;
    expect(states[states.length - 1]).toMatchObject({ kind: "error" });
    expect(rpc.calls.map((call) => call.params[1])).toEqual(["0x7b", "0x7b"]);
    expect(rpc.write).toHaveBeenCalledTimes(1);
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("stops after a reverted approval", async () => {
    rpc.wait.mockReset().mockResolvedValue({ status: "reverted", blockNumber: APPROVAL_BLOCK });
    const { states, refresh, done } = run();
    await done;
    expect(states[states.length - 1]).toEqual({ kind: "error", message: "The ACON approval transaction reverted." });
    expect(rpc.write).toHaveBeenCalledTimes(1);
    expect(rpc.calls).toEqual([]);
    expect(refresh).not.toHaveBeenCalled();
  });

  it("stops when the user rejects approval", async () => {
    rpc.write.mockReset().mockRejectedValue(new UserRejectedRequestError(new Error("Rejected")));
    const { states, done } = run();
    await done;
    expect(states[states.length - 1]).toEqual({ kind: "rejected" });
    expect(rpc.wait).not.toHaveBeenCalled();
    expect(rpc.calls).toEqual([]);
  });

  it("refreshes the mined allowance even when the buy signature is rejected", async () => {
    rpc.write.mockReset().mockResolvedValueOnce(APPROVAL)
      .mockRejectedValueOnce(new UserRejectedRequestError(new Error("Rejected")));
    const { states, refresh, done } = run();
    await done;
    expect(states[states.length - 1]).toEqual({ kind: "rejected" });
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(rpc.wait).toHaveBeenCalledTimes(1);
  });

  for (const error of ["SlippageExceeded", "InsufficientTokenAllowance"] as const) {
    it(`preserves a real ${error} failure without submitting or approving again`, async () => {
      rpc.contractError = error;
      const { states, refresh, done } = run();
      await done;
      expect(states[states.length - 1]).toMatchObject({ kind: "error" });
      expect((states[states.length - 1] as { message: string }).message).toMatch(
        error === "SlippageExceeded" ? /price moved/ : /not approved/,
      );
      expect(rpc.write).toHaveBeenCalledTimes(1);
      expect(refresh).toHaveBeenCalledTimes(1);
    });
  }

  it("uses latest and skips approval when the wallet is already approved", async () => {
    rpc.write.mockReset().mockResolvedValue(TRADE);
    const { states, done } = run({ ...buy, needsApproval: false });
    await done;
    expect(states[states.length - 1]).toMatchObject({ kind: "mined" });
    expect(rpc.calls.map((call) => call.params[1])).toEqual(["latest"]);
    expect(rpc.write).toHaveBeenCalledTimes(1);
  });

  it("does not reuse a previous approval block for a later buy", async () => {
    await run().done;
    rpc.calls = [];
    rpc.write.mockReset().mockResolvedValue(TRADE);
    const { done } = run({ ...buy, needsApproval: false });
    await done;
    expect(rpc.calls.map((call) => call.params[1])).toEqual(["latest"]);
    expect(rpc.write).toHaveBeenCalledTimes(1);
  });

  it("keeps sales on latest with their original minimum-return guard", async () => {
    rpc.write.mockReset().mockResolvedValue(TRADE);
    const { states, done } = run({
      account: ACCOUNT, market: MARKET, marketId: 1n, outcome: 0, shares: 4n * ONE,
      side: "sell", minReturn: 2n * ONE,
    });
    await done;
    expect(states[states.length - 1]).toMatchObject({ kind: "mined" });
    expect(rpc.calls[0].params[1]).toBe("latest");
    expect(rpc.write).toHaveBeenCalledTimes(1);
    expect(rpc.write.mock.calls[0][1]).toMatchObject({ functionName: "sell", args: [1n, 0, 4n * ONE, 2n * ONE] });
  });

  it("reports a mined-but-reverted buy without retrying a transaction", async () => {
    rpc.wait.mockReset().mockResolvedValueOnce({ status: "success", blockNumber: APPROVAL_BLOCK })
      .mockResolvedValueOnce({ status: "reverted", blockNumber: 124n });
    const { states, done } = run();
    await done;
    expect(states[states.length - 1]).toEqual({ kind: "reverted", hash: TRADE });
    expect(rpc.write).toHaveBeenCalledTimes(2);
  });
});
