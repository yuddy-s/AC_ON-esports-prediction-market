import type { Address, Hash } from "viem";
import { simulateContract, waitForTransactionReceipt, writeContract } from "wagmi/actions";
import { API_URL, CHAIN } from "./config";
import { describeError, isUserRejection } from "./errors";
import { aconTokenAbi, predictionMarketAbi, type Outcome } from "./predictionMarket";
import type { TradeStatus } from "./tradeStatus";
import { config } from "./wagmi";

interface TradeBase {
  account: Address;
  market: Address;
  marketId: bigint;
  outcome: Outcome;
  shares: bigint;
}

// Buy pays at most maxCost (approving exactly that much ACON first if
// needed); sell receives at least minReturn and needs no approval.
export type TradeRequest =
  | (TradeBase & { side: "buy"; token: Address; maxCost: bigint; needsApproval: boolean })
  | (TradeBase & { side: "sell"; minReturn: bigint });

// Keep the transaction sequence independent of React so approval/read ordering
// and wallet failures can be exercised without a signing wallet.
export async function executeTrade(
  request: TradeRequest,
  update: (status: TradeStatus) => void,
  refreshReads: () => void,
): Promise<void> {
  try {
    let approvalBlock: bigint | undefined;
    if (request.side === "buy" && request.needsApproval) {
      // Approve exactly maxCost, not an unlimited allowance.
      update({ kind: "approve-wallet" });
      const approveHash = await writeContract(config, {
        address: request.token,
        abi: aconTokenAbi,
        functionName: "approve",
        args: [request.market, request.maxCost],
        chainId: CHAIN.id,
      });
      update({ kind: "approve-pending", hash: approveHash });
      const approval = await waitForTransactionReceipt(config, { hash: approveHash, chainId: CHAIN.id });
      if (approval.status !== "success") {
        update({ kind: "error", message: "The ACON approval transaction reverted." });
        return;
      }
      approvalBlock = approval.blockNumber;
      // A later simulation or wallet rejection must not leave the UI showing
      // the allowance from before this successful approval.
      refreshReads();
    }

    // Simulate first so contract errors (slippage, deadline, balance)
    // show before the wallet prompt, decoded by name.
    update({ kind: "trade-wallet", side: request.side });
    const base = { account: request.account, address: request.market, abi: predictionMarketAbi, chainId: CHAIN.id } as const;
    let hash: Hash;
    if (request.side === "buy") {
      const args = [request.marketId, request.outcome, request.shares, request.maxCost] as const;
      await simulateContract(config, {
        ...base,
        functionName: "buy",
        args,
        // A fallback RPC's "latest" may predate the receipt returned by another
        // endpoint. Ask for the block that includes the mined approval instead.
        // Without a new approval, retain the normal latest-state preflight.
        blockNumber: approvalBlock,
      });
      // Forward only transaction fields: blockNumber selects simulation state,
      // while the contract still enforces maxCost against state at execution.
      hash = await writeContract(config, { ...base, functionName: "buy", args });
    } else {
      hash = await writeContract(config, (await simulateContract(config, {
        ...base,
        functionName: "sell",
        args: [request.marketId, request.outcome, request.shares, request.minReturn],
      })).request);
    }
    update({ kind: "submitted", hash });

    const receipt = await waitForTransactionReceipt(config, { hash, chainId: CHAIN.id });
    refreshReads();
    if (receipt.status !== "success") {
      update({ kind: "reverted", hash });
      return;
    }
    update({
      kind: "mined",
      hash,
      blockNumber: receipt.blockNumber,
      marketId: request.marketId,
      indexer: API_URL ? { state: "waiting", lastSafeBlock: null } : { state: "not-configured" },
    });
  } catch (error) {
    update(isUserRejection(error) ? { kind: "rejected" } : { kind: "error", message: describeError(error) });
  }
}
