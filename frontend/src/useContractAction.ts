import { useCallback, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { Address, Hash, Hex } from "viem";
import { simulateContract, waitForTransactionReceipt, writeContract } from "wagmi/actions";
import { CHAIN, PREDICTION_MARKET_ADDRESS } from "./config";
import { describeError, isUserRejection } from "./errors";
import { aconTokenAbi, predictionMarketAbi } from "./predictionMarket";
import { config } from "./wagmi";

// One-shot market writes (challenge, finalize, selection, vote, claim,
// surplus). Simulate first so contract errors show by name before the
// wallet prompt; mined and indexed stay separate from the trade flow.
export type ActionStatus =
  | { kind: "idle" }
  | { kind: "approve-wallet" }
  | { kind: "approve-pending"; hash: Hash }
  | { kind: "wallet" }
  | { kind: "pending"; hash: Hash }
  | { kind: "done"; hash: Hash }
  | { kind: "reverted"; hash: Hash }
  | { kind: "rejected" }
  | { kind: "error"; message: string };

// The market writes the UI makes, with their ABI argument types.
export type MarketCall =
  | { functionName: "createMarket"; args: readonly [Hex, bigint, Hex] }
  | { functionName: "challengeOutcome"; args: readonly [bigint, Hex] }
  | { functionName: "voteOnOutcome"; args: readonly [bigint, number] }
  | {
      functionName:
        | "finalize"
        | "requestResolverSelection"
        | "retryResolverSelection"
        | "advanceResolution"
        | "claimPayout"
        | "withdrawCreatorSurplus";
      args: readonly [bigint];
    };

export interface ActionRequest {
  account: Address;
  call: MarketCall;
  // Approve this much ACON to the market first (challenge bond, subsidy).
  approve?: { token: Address; amount: bigint };
}

// One typed branch per call shape so wagmi checks the arguments against the ABI.
async function send(account: Address, market: Address, call: MarketCall): Promise<Hash> {
  const base = { account, address: market, abi: predictionMarketAbi, chainId: CHAIN.id } as const;
  switch (call.functionName) {
    case "createMarket":
      return writeContract(config, (await simulateContract(config, { ...base, functionName: call.functionName, args: call.args })).request);
    case "challengeOutcome":
      return writeContract(config, (await simulateContract(config, { ...base, functionName: call.functionName, args: call.args })).request);
    case "voteOnOutcome":
      return writeContract(config, (await simulateContract(config, { ...base, functionName: call.functionName, args: call.args })).request);
    default:
      return writeContract(config, (await simulateContract(config, { ...base, functionName: call.functionName, args: call.args })).request);
  }
}

export function isActionBusy(status: ActionStatus): boolean {
  return ["approve-wallet", "approve-pending", "wallet", "pending"].includes(status.kind);
}

export function actionMessage(status: ActionStatus, verb: string): string {
  switch (status.kind) {
    case "idle":
      return "";
    case "approve-wallet":
      return "Step 1 of 2: approve the ACON in your wallet…";
    case "approve-pending":
      return "Approval submitted, waiting for it to be mined…";
    case "wallet":
      return `Confirm the ${verb} in your wallet…`;
    case "pending":
      return "Submitted. Waiting for the transaction to be mined…";
    case "done":
      return "Mined. The contract has been updated.";
    case "reverted":
      return "The transaction was mined but reverted. Nothing changed.";
    case "rejected":
      return "You rejected the request in your wallet. Nothing was sent.";
    case "error":
      return status.message;
  }
}

export function useContractAction() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<ActionStatus>({ kind: "idle" });
  const runId = useRef(0);

  const run = useCallback(
    async ({ account, call, approve }: ActionRequest) => {
      const market = PREDICTION_MARKET_ADDRESS;
      if (!market) return;
      const id = ++runId.current;
      const update = (next: ActionStatus) => {
        if (runId.current === id) setStatus(next);
      };
      try {
        if (approve) {
          update({ kind: "approve-wallet" });
          const approveHash = await writeContract(config, {
            address: approve.token,
            abi: aconTokenAbi,
            functionName: "approve",
            args: [market, approve.amount],
            chainId: CHAIN.id,
          });
          update({ kind: "approve-pending", hash: approveHash });
          const approval = await waitForTransactionReceipt(config, { hash: approveHash, chainId: CHAIN.id });
          if (approval.status !== "success") {
            update({ kind: "error", message: "The ACON approval transaction reverted." });
            return;
          }
        }
        update({ kind: "wallet" });
        const hash = await send(account, market, call);
        update({ kind: "pending", hash });
        const receipt = await waitForTransactionReceipt(config, { hash, chainId: CHAIN.id });
        void queryClient.invalidateQueries();
        update(receipt.status === "success" ? { kind: "done", hash } : { kind: "reverted", hash });
      } catch (error) {
        update(isUserRejection(error) ? { kind: "rejected" } : { kind: "error", message: describeError(error) });
      }
    },
    [queryClient],
  );

  const reset = useCallback(() => {
    runId.current++;
    setStatus({ kind: "idle" });
  }, []);

  return { status, run, reset };
}
