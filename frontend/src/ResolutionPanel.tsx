import { useState } from "react";
import { keccak256, toBytes, zeroAddress, type Address } from "viem";
import { useAccount, useReadContract, useReadContracts } from "wagmi";
import { ACON_TOKEN_ADDRESS, CHAIN, EXPLORER_URL, PREDICTION_MARKET_ADDRESS } from "./config";
import { Badge } from "./Badge";
import { formatTokenAmount, shortenAddress } from "./format";
import { marketPhase, type Action, type ResolutionView, type RoundView } from "./marketPhase";
import { formatCountdown } from "./marketTime";
import { aconTokenAbi, CHALLENGE_BOND, CHOICE, CHOICE_LABELS, OUTCOME, predictionMarketAbi } from "./predictionMarket";
import { Panel, PanelTitle } from "./ui";
import { actionMessage, isActionBusy, useContractAction, type MarketCall } from "./useContractAction";
import type { Market, MarketTeams } from "./useMarkets";
import { useChainNowSeconds } from "./useNow";
import { isWrongNetwork } from "./walletSupport";

const market = { address: PREDICTION_MARKET_ADDRESS, abi: predictionMarketAbi, chainId: CHAIN.id } as const;

// Proposal, challenge, resolver committee, settlement and claims for one
// market. The contract decides; the buttons shown come from marketPhase().
export function ResolutionPanel({ marketData, teams }: { marketData: Market; teams?: MarketTeams }) {
  const now = useChainNowSeconds();
  const { address } = useAccount();
  const id = marketData.id;

  const resolutionRead = useReadContract({ ...market, functionName: "getResolution", args: [id], query: { refetchInterval: 8_000 } });
  const resolution = resolutionRead.data as ResolutionView | undefined;
  const roundNumber = resolution?.round ?? 0;
  const roundRead = useReadContract({
    ...market,
    functionName: "getResolverRound",
    args: [id, roundNumber],
    query: { enabled: roundNumber > 0, refetchInterval: 8_000 },
  });
  const round = roundRead.data as (RoundView & { committee: readonly Address[]; voteCounts: readonly number[] }) | undefined;
  const phase = marketPhase(marketData, resolution, roundNumber > 0 ? round : undefined, now);

  return (
    <Panel>
      <PanelTitle tag="Resolution" title={phase.label} aside={<Badge tone={phase.tone}>{phase.key.replace(/-/g, " ")}</Badge>} />
      <p className="mt-3 text-cream">{phase.detail}</p>

      {resolution?.proposed && <Proposal resolution={resolution} teams={teams} now={now} />}
      {round && roundNumber > 0 && round.hasRequest !== undefined && <Committee round={round} roundNumber={roundNumber} you={address} />}

      <Actions marketData={marketData} resolution={resolution} roundNumber={roundNumber} actions={phase.actions} teams={teams} />
    </Panel>
  );
}

function choiceName(choice: number, teams?: MarketTeams): string {
  const label = CHOICE_LABELS[choice] ?? `#${choice}`;
  if (!teams || choice === CHOICE.VOID) return label;
  return `${label} (${choice === CHOICE.YES ? teams.teamA : teams.teamB} wins)`;
}

function Proposal({ resolution, teams, now }: { resolution: ResolutionView & { proposalEvidenceURI?: string }; teams?: MarketTeams; now: number }) {
  const challenged = resolution.challenger !== zeroAddress;
  return (
    <div className="mt-4 grid gap-3 border-t border-bronze/40 pt-3 text-sm sm:grid-cols-2">
      <div>
        <p className="label">Proposed result</p>
        <p className="mt-1 font-display text-lg font-semibold text-paper">{choiceName(resolution.proposal, teams)}</p>
        <p className="text-xs text-dust">
          by <span className="font-mono">{shortenAddress(resolution.proposer)}</span>
          {resolution.proposalEvidenceURI && (
            <>
              {" · "}
              <a href={resolution.proposalEvidenceURI} target="_blank" rel="noreferrer" className="link">
                evidence
              </a>
            </>
          )}
        </p>
      </div>
      <div>
        <p className="label">Challenge</p>
        {challenged ? (
          <p className="mt-1 text-signal">
            Challenged by <span className="font-mono">{shortenAddress(resolution.challenger)}</span> (10 ACON bond)
          </p>
        ) : (
          <p className="mt-1 num font-mono text-paper">
            {BigInt(Math.floor(now)) < resolution.challengeDeadline ? formatCountdown(resolution.challengeDeadline, now) + " left" : "Window closed"}
          </p>
        )}
      </div>
    </div>
  );
}

function Committee({
  round,
  roundNumber,
  you,
}: {
  round: RoundView & { committee: readonly Address[]; voteCounts: readonly number[] };
  roundNumber: number;
  you?: Address;
}) {
  const members = round.committee.filter((a) => a !== zeroAddress);
  return (
    <div className="mt-4 border-t border-bronze/40 pt-3">
      <p className="label">Resolver committee · round {roundNumber}</p>
      {members.length === 0 ? (
        <p className="mt-1 text-sm text-sand">No committee drawn yet.</p>
      ) : (
        <ul className="mt-2 flex flex-wrap gap-2">
          {members.map((m) => (
            <li key={m} className={`border px-2 py-0.5 font-mono text-xs ${m.toLowerCase() === you?.toLowerCase() ? "border-gold text-gold" : "border-bronze text-sand"}`}>
              {shortenAddress(m)}
              {m.toLowerCase() === you?.toLowerCase() && " · you"}
            </li>
          ))}
        </ul>
      )}
      {members.length > 0 && (
        <p className="mt-2 num font-mono text-xs text-sand">
          Votes: <span className="text-win">YES {round.voteCounts[0]}</span> · <span className="text-signal-soft">NO {round.voteCounts[1]}</span> · VOID{" "}
          {round.voteCounts[2]} <span className="text-dust">(3 matching settle it)</span>
        </p>
      )}
    </div>
  );
}

const VERBS: Record<Exclude<Action, "trade" | "vote" | "claim" | "challenge">, { label: string; fn: MarketCall["functionName"] }> = {
  finalize: { label: "Finalize the proposal", fn: "finalize" },
  "request-selection": { label: "Start resolver selection", fn: "requestResolverSelection" },
  "retry-selection": { label: "Request the committee draw", fn: "retryResolverSelection" },
  advance: { label: "Advance the market", fn: "advanceResolution" },
};

function Actions({
  marketData,
  resolution,
  roundNumber,
  actions,
  teams,
}: {
  marketData: Market;
  resolution: ResolutionView | undefined;
  roundNumber: number;
  actions: Action[];
  teams?: MarketTeams;
}) {
  const { address, chainId } = useAccount();
  const { status, run, reset } = useContractAction();
  const [reason, setReason] = useState("");
  const id = marketData.id;
  const user = address ?? zeroAddress;
  const token = ACON_TOKEN_ADDRESS;

  const reads = useReadContracts({
    contracts: [
      { ...market, functionName: "isSelectedResolver", args: [id, roundNumber, user] },
      { ...market, functionName: "hasVoted", args: [id, roundNumber, user] },
      { ...market, functionName: "claimableAmount", args: [id, user] },
      { ...market, functionName: "hasClaimed", args: [id, user] },
      { ...market, functionName: "balanceOf", args: [id, user, OUTCOME.YES] },
      { ...market, functionName: "balanceOf", args: [id, user, OUTCOME.NO] },
      { ...market, functionName: "withdrawableSurplus", args: [id] },
      { address: token, abi: aconTokenAbi, functionName: "allowance", args: [user, PREDICTION_MARKET_ADDRESS ?? zeroAddress], chainId: CHAIN.id },
      { address: token, abi: aconTokenAbi, functionName: "balanceOf", args: [user], chainId: CHAIN.id },
    ],
    allowFailure: false,
    query: { enabled: address !== undefined && token !== undefined, refetchInterval: 8_000 },
  });
  const [selected, voted, claimable, claimed, yes, no, surplus, allowance, acon] = reads.data ?? [];

  if (!address) {
    return <p className="mt-4 text-sm text-sand">Connect a wallet to challenge, vote or claim.</p>;
  }
  const busy = isActionBusy(status);
  const wrong = isWrongNetwork(chainId, CHAIN.id);
  const go = (call: MarketCall, approve?: { token: `0x${string}`; amount: bigint }) => void run({ account: address, call, approve });
  const isProposer = resolution?.proposer.toLowerCase() === address.toLowerCase();
  const isCreator = marketData.creator.toLowerCase() === address.toLowerCase();
  const hasPosition = (yes ?? 0n) > 0n || (no ?? 0n) > 0n;
  const disabled = busy || wrong;

  return (
    <div className="mt-4 flex flex-col gap-3 border-t border-bronze/40 pt-3">
      {actions.includes("challenge") &&
        (isProposer ? (
          <p className="text-sm text-sand">You proposed this result, so you can't challenge it.</p>
        ) : (
          <div className="flex flex-col gap-2">
            <label className="flex flex-col gap-1.5">
              <span className="label">Why is it wrong? (link or reason, stored as a hash)</span>
              <input value={reason} onChange={(e) => setReason(e.target.value)} disabled={disabled} className="field text-sm" placeholder="https://… or a short reason" />
            </label>
            <button
              className="btn-gold"
              disabled={disabled || !token || reason.trim() === "" || (acon !== undefined && acon < CHALLENGE_BOND)}
              onClick={() =>
                go(
                  { functionName: "challengeOutcome", args: [id, keccak256(toBytes(reason.trim()))] },
                  allowance !== undefined && allowance < CHALLENGE_BOND && token ? { token, amount: CHALLENGE_BOND } : undefined,
                )
              }
            >
              {allowance !== undefined && allowance < CHALLENGE_BOND ? "Approve 10 ACON, then challenge" : "Challenge with 10 ACON bond"}
            </button>
            <p className="text-xs text-dust">
              The bond is refunded if the final result differs from the proposal, and kept by the market if the proposal is upheld.
            </p>
            {acon !== undefined && acon < CHALLENGE_BOND && <p className="text-sm text-signal">You need 10 ACON for the bond.</p>}
          </div>
        ))}

      {(Object.keys(VERBS) as (keyof typeof VERBS)[])
        .filter((a) => actions.includes(a))
        .map((a) => (
          <button key={a} className="btn-ghost self-start border-gold text-gold" disabled={disabled} onClick={() => go({ functionName: VERBS[a].fn, args: [id] } as MarketCall)}>
            {VERBS[a].label}
          </button>
        ))}

      {actions.includes("vote") &&
        (selected ? (
          voted ? (
            <p className="text-sm text-win">You already voted in this round.</p>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="label">Your vote (selected resolver)</p>
              <div className="grid grid-cols-3 gap-2">
                {[CHOICE.YES, CHOICE.NO, CHOICE.VOID].map((c) => (
                  <button
                    key={c}
                    disabled={disabled}
                    onClick={() => go({ functionName: "voteOnOutcome", args: [id, c] })}
                    className={`border py-2 font-display text-sm font-bold tracking-wider ${
                      c === CHOICE.YES ? "border-win text-win hover:bg-win/10" : c === CHOICE.NO ? "border-signal-soft text-signal-soft hover:bg-signal/10" : "border-bronze text-sand hover:bg-ink-600"
                    }`}
                  >
                    {CHOICE_LABELS[c]}
                    {teams && c !== CHOICE.VOID && <span className="block truncate px-1 text-[10px] font-semibold normal-case opacity-80">{c === CHOICE.YES ? teams.teamA : teams.teamB}</span>}
                  </button>
                ))}
              </div>
            </div>
          )
        ) : (
          <p className="text-sm text-sand">Only the five selected resolvers can vote. This wallet is not on the committee.</p>
        ))}

      {actions.includes("claim") &&
        (claimed ? (
          <p className="text-sm text-win">You already claimed your payout for this market.</p>
        ) : hasPosition ? (
          <button className="btn-gold" disabled={disabled} onClick={() => go({ functionName: "claimPayout", args: [id] })}>
            Claim {formatTokenAmount(claimable ?? 0n, 18, 4)} ACON
          </button>
        ) : (
          <p className="text-sm text-sand">This wallet has no shares to claim in this market.</p>
        ))}
      {actions.includes("claim") && claimable === 0n && hasPosition && !claimed && (
        <p className="-mt-2 text-xs text-dust">Your shares are on the losing side, so the claim pays 0 ACON but closes your position.</p>
      )}

      {isCreator && (surplus ?? 0n) > 0n && (
        <button className="btn-ghost self-start" disabled={disabled} onClick={() => go({ functionName: "withdrawCreatorSurplus", args: [id] })}>
          Withdraw creator surplus · {formatTokenAmount(surplus ?? 0n, 18, 4)} ACON
        </button>
      )}

      {status.kind !== "idle" && (
        <div className="border border-bronze/50 bg-ink-900 p-3 text-sm">
          <p className={["error", "reverted", "rejected"].includes(status.kind) ? "text-signal" : "text-cream"}>{actionMessage(status, "transaction")}</p>
          {"hash" in status && EXPLORER_URL && (
            <a href={`${EXPLORER_URL}/tx/${status.hash}`} target="_blank" rel="noreferrer" className="link font-mono text-xs">
              {status.hash.slice(0, 10)}…{status.hash.slice(-6)}
            </a>
          )}
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
