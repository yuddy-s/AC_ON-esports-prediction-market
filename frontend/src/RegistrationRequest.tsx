import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAccount, useSignMessage } from "wagmi";
import { CHAIN, FIXTURE_SOURCE } from "./config";
import { isUserRejection } from "./errors";
import type { Fixture } from "./fixturesApi";
import { registrationEligibility, type JobSummary } from "./fixtureStatus";
import {
  createRegistrationChallenge,
  describeRegistrationError,
  RegistrationApiError,
  submitRegistrationRequest,
} from "./registrationApi";
import { isWrongNetwork } from "./walletSupport";

type Step =
  | { kind: "idle" }
  | { kind: "busy"; message: string }
  | { kind: "done" }
  | { kind: "error"; message: string; canRetry: boolean };

const COINBASE_CONNECTOR_ID = "coinbaseWalletSDK";

// Asks the backend's registrar to register this fixture on-chain. The player
// signs a message, not a transaction: no gas, and no market is created yet.
export function RegistrationRequest({ fixture, job, nowMs }: { fixture: Fixture; job: JobSummary | null | undefined; nowMs: number }) {
  const { address, connector, chainId } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>({ kind: "idle" });

  if (step.kind === "done") {
    return <p className="mt-2 text-sm text-emerald-300">Request sent. The registration status above updates as the registrar works.</p>;
  }

  // Also covers a recoverable terminal failure, which accepts a fresh signature.
  const eligibility = registrationEligibility(fixture, nowMs, job);
  if (!eligibility.ok) return null;
  const retrying = fixture.registration_request_status === "terminal_failure";

  let blocker: string | null = null;
  if (FIXTURE_SOURCE === "mock") blocker = "Registration requests need the backend (mock fixtures are read-only).";
  else if (!address) blocker = "Connect a wallet to request registration.";
  else if (isWrongNetwork(chainId, CHAIN.id)) blocker = `Switch your wallet to ${CHAIN.name} to request registration.`;
  else if (connector?.id === COINBASE_CONNECTOR_ID) {
    blocker = "Registration needs a regular wallet signature. Connect MetaMask (Coinbase Smart Wallet signatures are not supported).";
  }

  async function request() {
    if (!address) return;
    try {
      setStep({ kind: "busy", message: "Getting a signing request from the backend…" });
      const challenge = await createRegistrationChallenge(fixture.id, address);
      if (challenge.chain_id !== CHAIN.id) {
        setStep({ kind: "error", message: `The backend is configured for chain ${challenge.chain_id}, not ${CHAIN.name}.`, canRetry: false });
        return;
      }
      setStep({ kind: "busy", message: "Sign the message in your wallet (no gas, no transaction)…" });
      const signature = await signMessageAsync({ account: address, message: challenge.message });
      setStep({ kind: "busy", message: "Sending the signed request…" });
      await submitRegistrationRequest(fixture.id, address, challenge.nonce, signature);
      setStep({ kind: "done" });
      await queryClient.invalidateQueries({ queryKey: ["fixture"] });
      await queryClient.invalidateQueries({ queryKey: ["fixtures"] });
      await queryClient.invalidateQueries({ queryKey: ["fixture-registration"] });
    } catch (error) {
      if (isUserRejection(error)) {
        setStep({ kind: "error", message: "You rejected the signature. Nothing was sent.", canRetry: true });
      } else if (error instanceof RegistrationApiError) {
        setStep({ kind: "error", ...describeRegistrationError(error.code) });
      } else {
        setStep({ kind: "error", message: "Could not reach the backend. Try again in a moment.", canRetry: true });
      }
    }
  }

  const busy = step.kind === "busy";
  const canClick = blocker === null && !busy && (step.kind !== "error" || step.canRetry);

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={request}
        disabled={!canClick}
        className="w-full rounded bg-amber-400 px-3 py-2 text-sm font-semibold text-neutral-900 hover:bg-amber-300 disabled:bg-neutral-800 disabled:text-neutral-500"
      >
        {busy ? "Requesting…" : retrying ? "Request registration again" : "Request on-chain registration"}
      </button>
      <p className="mt-1 text-xs text-neutral-500">
        You sign a message (free). The team's registrar then registers the fixture on-chain.
      </p>
      {blocker && <p className="mt-1 text-sm text-amber-300">{blocker}</p>}
      {step.kind === "busy" && <p className="mt-1 text-sm text-neutral-300">{step.message}</p>}
      {step.kind === "error" && <p className="mt-1 text-sm text-red-400">{step.message}</p>}
    </div>
  );
}
