import { CHOICE_LABELS, MARKET_STATE, NO_PROPOSAL_PERIOD_SECONDS, RETRY_DELAY_SECONDS } from "./predictionMarket";
import type { Tone } from "./fixtureStatus";

// One rule for what a market is doing right now and which calls are valid.
// Stored state alone is not enough: time passing does not change storage, so
// an OPEN market past its deadline is closed for trading (M3 feedback) and
// expired windows need a caller to advance them (CONTRACT_ABI.md).

export interface ResolutionView {
  proposed: boolean;
  proposal: number;
  proposer: string;
  challengeDeadline: bigint;
  challenger: string;
  round: number;
  terminal: boolean;
  finalOutcome: number;
}

export interface RoundView {
  selectionDeadline: bigint;
  voteDeadline: bigint;
  lastRequestAt: bigint;
  hasRequest: boolean;
  fulfilled: boolean;
}

export type Action =
  | "trade"
  | "challenge"
  | "finalize"
  | "request-selection"
  | "retry-selection"
  | "advance"
  | "vote"
  | "claim";

export interface Phase {
  key: "trading" | "awaiting-proposal" | "no-proposal" | "challenge-window" | "ready-to-finalize" | "disputed"
    | "selecting" | "selection-expired" | "voting" | "voting-expired" | "finalized" | "void";
  label: string;
  tone: Tone;
  detail: string;
  actions: Action[];
}

const date = (seconds: bigint) => new Date(Number(seconds) * 1000).toLocaleString();

export function marketPhase(
  market: { state: number; tradingDeadline: bigint },
  resolution: ResolutionView | undefined,
  round: RoundView | undefined,
  nowSeconds: number,
): Phase {
  const now = BigInt(Math.floor(nowSeconds));
  const proposal = resolution?.proposed ? CHOICE_LABELS[resolution.proposal] : undefined;

  switch (market.state) {
    case MARKET_STATE.OPEN:
      if (now < market.tradingDeadline) {
        return { key: "trading", label: "Trading", tone: "good", detail: `Trading closes ${date(market.tradingDeadline)}.`, actions: ["trade"] };
      }
    // Past the deadline an OPEN market behaves exactly like CLOSED.
    // falls through
    case MARKET_STATE.CLOSED: {
      const cutoff = market.tradingDeadline + NO_PROPOSAL_PERIOD_SECONDS;
      if (now >= cutoff) {
        return {
          key: "no-proposal",
          label: "No result proposed",
          tone: "warn",
          detail: "No result was proposed within seven days of the deadline. Anyone can start resolver selection.",
          actions: ["request-selection"],
        };
      }
      return {
        key: "awaiting-proposal",
        label: "Trading closed",
        tone: "neutral",
        detail: `Waiting for the result proposal. If none arrives by ${date(cutoff)}, anyone can start resolver selection.`,
        actions: [],
      };
    }
    case MARKET_STATE.PROPOSED:
      if (resolution && now < resolution.challengeDeadline) {
        return {
          key: "challenge-window",
          label: `Proposed: ${proposal}`,
          tone: "warn",
          detail: `Anyone except the proposer can challenge with a 10 ACON bond until ${date(resolution.challengeDeadline)}.`,
          actions: ["challenge"],
        };
      }
      return {
        key: "ready-to-finalize",
        label: `Proposed: ${proposal}`,
        tone: "warn",
        detail: "The challenge window is over with no challenge. Anyone can finalize the proposal.",
        actions: ["finalize"],
      };
    case MARKET_STATE.DISPUTED:
      return {
        key: "disputed",
        label: "Disputed",
        tone: "bad",
        detail: `The proposed ${proposal ?? "result"} was challenged. Anyone can start resolver selection.`,
        actions: ["request-selection"],
      };
    case MARKET_STATE.RESOLVER_SELECTION:
      if (round && now >= round.selectionDeadline) {
        return {
          key: "selection-expired",
          label: "Selection expired",
          tone: "bad",
          detail: "No committee formed before the deadline. Anyone can advance the market, which voids it.",
          actions: ["advance"],
        };
      }
      return {
        key: "selecting",
        label: `Selecting resolvers · round ${resolution?.round ?? 1}`,
        tone: "warn",
        detail: round?.hasRequest
          ? "Waiting for the random committee draw (Chainlink VRF)."
          : "Not enough eligible resolvers yet, or the last request failed. The draw can be requested again.",
        actions: !round || !round.hasRequest || now >= round.lastRequestAt + RETRY_DELAY_SECONDS ? ["retry-selection"] : [],
      };
    case MARKET_STATE.RESOLVER_VOTING:
      if (round && now >= round.voteDeadline) {
        return {
          key: "voting-expired",
          label: "Voting expired",
          tone: "bad",
          detail:
            resolution?.round === 1
              ? "Round 1 ended without three matching votes. Anyone can advance to a replacement committee."
              : "Round 2 ended without three matching votes. Anyone can advance the market, which voids it.",
          actions: ["advance"],
        };
      }
      return {
        key: "voting",
        label: `Resolver vote · round ${resolution?.round ?? 1}`,
        tone: "warn",
        detail: round ? `Selected resolvers vote YES, NO or VOID until ${date(round.voteDeadline)}. Three matching votes settle it.` : "Selected resolvers are voting.",
        actions: ["vote"],
      };
    case MARKET_STATE.FINALIZED:
      return {
        key: "finalized",
        label: `Final: ${resolution ? CHOICE_LABELS[resolution.finalOutcome] : "?"}`,
        tone: "good",
        detail: "Settled. Winning shares pay 1 ACON each; claim once.",
        actions: ["claim"],
      };
    case MARKET_STATE.VOID:
      return {
        key: "void",
        label: "Void",
        tone: "neutral",
        detail: "Voided. Every share pays 0.5 ACON; YES and NO holdings are claimed together, once.",
        actions: ["claim"],
      };
    default:
      return { key: "awaiting-proposal", label: `Unknown state ${market.state}`, tone: "bad", detail: "", actions: [] };
  }
}
