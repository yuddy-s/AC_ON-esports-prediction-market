import { useState } from "react";
import { zeroAddress, type Hex } from "viem";
import { useAccount, useReadContract, useReadContracts } from "wagmi";
import { ACON_TOKEN_ADDRESS, CHAIN, PREDICTION_MARKET_ADDRESS } from "./config";
import { formatTokenAmount } from "./format";
import type { Fixture } from "./fixturesApi";
import { aconTokenAbi, MIN_START_MARGIN_SECONDS, predictionMarketAbi, REQUIRED_SUBSIDY } from "./predictionMarket";
import { marketHref } from "./router";
import { actionMessage, isActionBusy, useContractAction } from "./useContractAction";
import { useChainNowSeconds } from "./useNow";
import { isWrongNetwork } from "./walletSupport";

const market = { address: PREDICTION_MARKET_ADDRESS, abi: predictionMarketAbi, chainId: CHAIN.id } as const;

interface OnChainFixture {
  data: { teamAName: string; teamBName: string; scheduledStart: bigint };
  revisionHash: Hex;
  registered: boolean;
  hasMarket: boolean;
  marketId: bigint;
}

// Latest allowed trading deadline: 15 minutes before the registered start.
export function maxDeadline(scheduledStart: bigint): bigint {
  return scheduledStart - MIN_START_MARGIN_SECONDS;
}

// "2026-11-20T17:30" in the browser's time zone <-> Unix seconds.
export function toLocalInput(seconds: bigint): string {
  const d = new Date(Number(seconds) * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fromLocalInput(value: string): bigint | undefined {
  const ms = new Date(value).getTime();
  return Number.isFinite(ms) ? BigInt(Math.floor(ms / 1000)) : undefined;
}

export function deadlineProblem(deadline: bigint | undefined, nowSeconds: number, scheduledStart: bigint): string | null {
  if (deadline === undefined) return "Pick a trading deadline.";
  if (deadline <= BigInt(Math.floor(nowSeconds))) return "The deadline must be in the future.";
  if (deadline > maxDeadline(scheduledStart)) return "Trading must close at least 15 minutes before the match starts.";
  return null;
}

// The contract's view of a catalog fixture (key from the source identity).
// This, not the backend job status, is authoritative for registration.
export function useOnChainFixture(fixture: Fixture) {
  const keyRead = useReadContract({
    ...market,
    functionName: "computeFixtureKey",
    args: [fixture.provider_id, fixture.game_id, fixture.external_match_id],
    query: { enabled: PREDICTION_MARKET_ADDRESS !== undefined },
  });
  const fixtureRead = useReadContract({
    ...market,
    functionName: "getFixture",
    args: [keyRead.data ?? "0x"],
    query: { enabled: keyRead.data !== undefined, refetchInterval: 10_000 },
  });
  return { key: keyRead.data, onChain: fixtureRead.data as OnChainFixture | undefined };
}

// Funds the one market a registered fixture may have. The chain, not the
// backend job status, decides whether the fixture is registered and free.
export function CreateMarket({ fixture }: { fixture: Fixture }) {
  const { address, chainId } = useAccount();
  const now = useChainNowSeconds();
  const { status, run, reset } = useContractAction();
  const [deadlineInput, setDeadlineInput] = useState<string | null>(null);

  const { key, onChain } = useOnChainFixture(fixture);
  const wallet = useReadContracts({
    contracts: [
      { address: ACON_TOKEN_ADDRESS, abi: aconTokenAbi, functionName: "balanceOf", args: [address ?? zeroAddress], chainId: CHAIN.id },
      { address: ACON_TOKEN_ADDRESS, abi: aconTokenAbi, functionName: "allowance", args: [address ?? zeroAddress, PREDICTION_MARKET_ADDRESS ?? zeroAddress], chainId: CHAIN.id },
    ],
    allowFailure: false,
    query: { enabled: address !== undefined && ACON_TOKEN_ADDRESS !== undefined },
  });
  const [acon, allowance] = wallet.data ?? [];

  if (!PREDICTION_MARKET_ADDRESS) return null;
  if (!onChain) return <p className="text-xs text-dust">Checking the on-chain registration…</p>;
  if (!onChain.registered) {
    return (
      <button type="button" disabled className="btn-gold w-full">
        Create market · after on-chain registration
      </button>
    );
  }
  if (onChain.hasMarket) {
    return (
      <a href={marketHref(onChain.marketId)} className="btn-gold block w-full text-center">
        Go to market #{onChain.marketId.toString()} →
      </a>
    );
  }

  const latest = maxDeadline(onChain.data.scheduledStart);
  const deadline = fromLocalInput(deadlineInput ?? toLocalInput(latest));
  const problem = deadlineProblem(deadline, now, onChain.data.scheduledStart);
  const needsApproval = allowance !== undefined && allowance < REQUIRED_SUBSIDY;
  const tooPoor = acon !== undefined && acon < REQUIRED_SUBSIDY;
  const busy = isActionBusy(status);
  const blocked = !address || isWrongNetwork(chainId, CHAIN.id) || busy || problem !== null || tooPoor || key === undefined;

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm text-win">Registered on-chain: {onChain.data.teamAName} (YES) vs {onChain.data.teamBName} (NO).</p>
      <label className="flex flex-col gap-1.5">
        <span className="label">Trading deadline</span>
        <input
          type="datetime-local"
          value={deadlineInput ?? toLocalInput(latest)}
          max={toLocalInput(latest)}
          onChange={(e) => setDeadlineInput(e.target.value)}
          disabled={busy}
          className="field text-sm"
        />
      </label>
      {problem && <p className="text-sm text-signal">{problem}</p>}
      <button
        className="btn-gold w-full"
        disabled={blocked}
        onClick={() =>
          address &&
          key &&
          deadline !== undefined &&
          void run({
            account: address,
            call: { functionName: "createMarket", args: [key, deadline, onChain.revisionHash] },
            approve: needsApproval && ACON_TOKEN_ADDRESS ? { token: ACON_TOKEN_ADDRESS, amount: REQUIRED_SUBSIDY } : undefined,
          })
        }
      >
        {needsApproval ? "Approve subsidy, then create market" : "Create market"}
      </button>
      <p className="text-xs text-dust">
        Creating the market funds it with the fixed LMSR subsidy of {formatTokenAmount(REQUIRED_SUBSIDY, 18, 4)} ACON. One market per fixture.
      </p>
      {!address && <p className="text-sm text-gold">Connect a wallet to create the market.</p>}
      {tooPoor && <p className="text-sm text-signal">You need {formatTokenAmount(REQUIRED_SUBSIDY, 18, 2)} ACON for the subsidy.</p>}
      {status.kind !== "idle" && (
        <div className="border border-bronze/50 bg-ink-900 p-3 text-sm">
          <p className={["error", "reverted", "rejected"].includes(status.kind) ? "text-signal" : "text-cream"}>{actionMessage(status, "market creation")}</p>
          {!busy && (
            <button onClick={reset} className="link mt-1 block text-xs">
              Dismiss
            </button>
          )}
        </div>
      )}
    </div>
  );
}
