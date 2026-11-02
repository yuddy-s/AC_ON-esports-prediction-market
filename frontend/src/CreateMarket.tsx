import { useState } from "react";
import { encodeAbiParameters, keccak256, zeroAddress, type Hex } from "viem";
import { useAccount, useReadContract, useReadContracts } from "wagmi";
import { ACON_TOKEN_ADDRESS, CHAIN, PREDICTION_MARKET_ADDRESS } from "./config";
import { isContractRevert } from "./errors";
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

// What the chain says about a fixture. getFixture reverts FixtureNotRegistered
// for an unregistered key; that revert is an answer ("not registered"), while
// RPC, network or provider failures are not and stay retryable errors.
export type RegistrationRead =
  | { kind: "loading" }
  | { kind: "registered"; fixture: OnChainFixture }
  | { kind: "not-registered" }
  | { kind: "error"; message: string };

export function registrationRead(input: { fixtureError: unknown; data: OnChainFixture | undefined }): RegistrationRead {
  if (input.data) return input.data.registered ? { kind: "registered", fixture: input.data } : { kind: "not-registered" };
  if (isContractRevert(input.fixtureError, "FixtureNotRegistered")) return { kind: "not-registered" };
  const failure = input.fixtureError;
  if (failure) {
    const message = failure instanceof Error ? failure.message.split("\n")[0] : String(failure);
    return { kind: "error", message };
  }
  return { kind: "loading" };
}

// computeFixtureKey(providerId, gameId, externalMatchId) is
// keccak256(abi.encode(string,string,string)) with no normalization
// (CONTRACT_ABI.md), so it is computed locally instead of over RPC.
export function fixtureKey(providerId: string, gameId: string, externalMatchId: string): Hex {
  return keccak256(encodeAbiParameters([{ type: "string" }, { type: "string" }, { type: "string" }], [providerId, gameId, externalMatchId]));
}

// Retrying a deterministic contract revert only delays the answer.
const retryUnlessNotRegistered = (failureCount: number, error: unknown) =>
  !isContractRevert(error, "FixtureNotRegistered") && failureCount < 2;

// The contract's view of a catalog fixture (key from the source identity).
// This, not the backend job status, is authoritative for registration.
export function useOnChainFixture(fixture: Fixture) {
  const key = fixtureKey(fixture.provider_id, fixture.game_id, fixture.external_match_id);
  const fixtureRead = useReadContract({
    ...market,
    functionName: "getFixture",
    args: [key],
    query: { enabled: PREDICTION_MARKET_ADDRESS !== undefined, refetchInterval: 10_000, retry: retryUnlessNotRegistered },
  });
  const data = fixtureRead.data as OnChainFixture | undefined;
  return {
    key,
    onChain: data,
    read: registrationRead({ fixtureError: fixtureRead.error, data }),
    retry: () => void fixtureRead.refetch(),
  };
}

// Registration as the chain sees it for a list of catalog fixtures: true or
// false when the contract answered, missing when the read failed (the caller
// then falls back to the backend job status rather than guessing).
export function useOnChainRegistrations(fixtures: readonly Fixture[]): Map<number, boolean> {
  const records = useReadContracts({
    contracts: fixtures.map((f) => ({
      ...market,
      functionName: "getFixture" as const,
      args: [fixtureKey(f.provider_id, f.game_id, f.external_match_id)] as const,
    })),
    // Unregistered keys revert; one revert must not fail the whole list.
    allowFailure: true,
    query: { enabled: PREDICTION_MARKET_ADDRESS !== undefined && fixtures.length > 0, refetchInterval: 15_000 },
  });
  const map = new Map<number, boolean>();
  records.data?.forEach((r, i) => {
    if (r.status === "success") map.set(fixtures[i].id, (r.result as OnChainFixture).registered);
    else if (isContractRevert(r.error, "FixtureNotRegistered")) map.set(fixtures[i].id, false);
  });
  return map;
}

// Funds the one market a registered fixture may have. The chain, not the
// backend job status, decides whether the fixture is registered and free.
export function CreateMarket({ fixture }: { fixture: Fixture }) {
  const { address, chainId } = useAccount();
  const now = useChainNowSeconds();
  const { status, run, reset } = useContractAction();
  const [deadlineInput, setDeadlineInput] = useState<string | null>(null);

  const { key, read, retry } = useOnChainFixture(fixture);
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
  if (read.kind === "loading") return <p className="text-xs text-dust">Checking the on-chain registration…</p>;
  if (read.kind === "error") {
    return (
      <div className="flex flex-col gap-1.5">
        <p className="text-sm text-signal">Couldn't read the on-chain registration. Check the network and try again.</p>
        <p className="break-words font-mono text-[11px] text-dust">{read.message}</p>
        <button type="button" onClick={retry} className="btn-ghost self-start">
          Retry
        </button>
      </div>
    );
  }
  if (read.kind === "not-registered") {
    return (
      <button type="button" disabled className="btn-gold w-full">
        Create market · after on-chain registration
      </button>
    );
  }
  const onChain = read.fixture;
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
