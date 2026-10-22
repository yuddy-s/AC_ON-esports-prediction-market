import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAccount, useReadContracts, useWaitForTransactionReceipt, useWriteContract } from "wagmi";
import { ACON_TOKEN_ADDRESS, CHAIN } from "./config";
import { isWrongNetwork } from "./walletSupport";
import { formatTokenAmount } from "./format";
import { aconTokenAbi } from "./predictionMarket";

// ACON is the market's payment token (Sepolia ETH only pays gas).
// Each address can claim the faucet once for 1,000 ACON.
export function AconPanel() {
  const { address, isConnected, chainId: walletChainId } = useAccount();

  const reads = useReadContracts({
    contracts: [
      { address: ACON_TOKEN_ADDRESS, abi: aconTokenAbi, functionName: "balanceOf", args: [address!], chainId: CHAIN.id },
      { address: ACON_TOKEN_ADDRESS, abi: aconTokenAbi, functionName: "hasClaimedFaucet", args: [address!], chainId: CHAIN.id },
    ],
    allowFailure: false,
    query: { enabled: isConnected && address !== undefined && ACON_TOKEN_ADDRESS !== undefined },
  });

  const claim = useWriteContract();
  const receipt = useWaitForTransactionReceipt({ hash: claim.data, chainId: CHAIN.id });

  // Once the faucet transaction is mined, refresh every read on the page
  // (this panel and the trade form both show the ACON balance).
  const queryClient = useQueryClient();
  useEffect(() => {
    if (receipt.isSuccess) void queryClient.invalidateQueries();
  }, [receipt.isSuccess, queryClient]);

  if (!isConnected) return null;

  if (!ACON_TOKEN_ADDRESS) {
    return (
      <section className="rounded-lg border border-neutral-700 bg-neutral-900 p-5 text-sm text-red-400">
        VITE_ACON_TOKEN_ADDRESS is not set (see frontend/.env.example).
      </section>
    );
  }

  const token = ACON_TOKEN_ADDRESS;
  const [balance, hasClaimed] = reads.data ?? [];
  const claiming = claim.isPending || (claim.data !== undefined && receipt.isLoading);

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-neutral-700 bg-neutral-900 p-5">
      <div>
        <p className="text-sm text-neutral-400">ACON balance (pays for trades)</p>
        <p className="font-mono text-lg">
          {balance !== undefined ? `${formatTokenAmount(balance)} ACON` : "Loading..."}
        </p>
      </div>

      {hasClaimed === false && (
        <button
          onClick={() => claim.writeContract({ address: token, abi: aconTokenAbi, functionName: "faucet", chainId: CHAIN.id })}
          disabled={claiming || isWrongNetwork(walletChainId, CHAIN.id)}
          className="self-start rounded-lg bg-amber-400 px-4 py-2 text-sm font-semibold text-neutral-900 hover:bg-amber-300 disabled:opacity-50"
        >
          {claim.isPending ? "Confirm in wallet..." : claiming ? "Claiming..." : "Claim 1,000 ACON"}
        </button>
      )}
      {hasClaimed === true && (
        <p className="text-xs text-neutral-500">Faucet already claimed for this wallet (one claim per address).</p>
      )}

      {receipt.isSuccess && receipt.data.status === "success" && (
        <p className="text-sm text-emerald-300">Claimed 1,000 ACON.</p>
      )}
      {(claim.error || receipt.error || receipt.data?.status === "reverted") && (
        <p className="break-words text-sm text-red-400">
          Claim failed: {(claim.error ?? receipt.error)?.message.split("\n")[0] ?? "transaction reverted"}
        </p>
      )}
    </section>
  );
}
