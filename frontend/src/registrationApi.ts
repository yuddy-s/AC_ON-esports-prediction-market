import { API_URL } from "./config";
import type { RegistrationStatus } from "./fixturesApi";

// Player-driven fixture registration (M4_BACKEND_API.md): get a challenge,
// sign its exact message with the wallet (EIP-191), then submit the request.
// A job is only a request; "confirmed" is the only status that means the
// fixture is registered on-chain.

export interface RegistrationChallenge {
  nonce: string;
  message: string;
  expires_at: string;
  chain_id: number;
}

export interface RegistrationJob {
  id: number;
  fixture_id: number;
  requested_by: string;
  chain_id: number;
  status: RegistrationStatus;
  transaction_hash: string | null;
  error_code: string | null;
  attempts: number;
  next_attempt_at: string | null;
  created_at: string;
  updated_at: string;
}

// A backend rejection with its stable code (detail.code), so the UI can say
// something specific instead of showing raw server text.
export class RegistrationApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "RegistrationApiError";
  }
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    const code = typeof detail?.code === "string" ? detail.code : "http_error";
    const message = typeof detail?.message === "string" ? detail.message : `${path} returned HTTP ${response.status}`;
    throw new RegistrationApiError(code, message, response.status);
  }
  return (await response.json()) as T;
}

export function createRegistrationChallenge(fixtureId: number, wallet: string): Promise<RegistrationChallenge> {
  return postJson(`/api/fixtures/${fixtureId}/registration-challenges`, { wallet_address: wallet });
}

export function submitRegistrationRequest(
  fixtureId: number,
  wallet: string,
  nonce: string,
  signature: string,
): Promise<RegistrationJob> {
  return postJson(`/api/fixtures/${fixtureId}/registration-requests`, { wallet_address: wallet, nonce, signature });
}

// null means nobody has requested registration yet.
export async function fetchRegistration(fixtureId: number, signal?: AbortSignal): Promise<RegistrationJob | null> {
  const response = await fetch(`${API_URL}/api/fixtures/${fixtureId}/registration`, { signal });
  if (!response.ok) throw new Error(`/api/fixtures/${fixtureId}/registration returned HTTP ${response.status}`);
  return (await response.json()) as RegistrationJob | null;
}

export function describeRegistrationError(code: string): { message: string; canRetry: boolean } {
  switch (code) {
    case "invalid_address":
      return { message: "The backend did not accept this wallet address.", canRetry: false };
    case "fixture_not_found":
      return { message: "This fixture no longer exists in the catalog.", canRetry: false };
    case "fixture_ineligible":
      return {
        message: "This fixture can't be registered (it is not scheduled, already has a result, or starts too soon).",
        canRetry: false,
      };
    case "fixture_changed":
      return { message: "The fixture details changed while you were signing. Review them and request again.", canRetry: true };
    case "invalid_challenge":
      return { message: "The signing request expired or was already used. Request again to get a new one.", canRetry: true };
    case "invalid_signature":
      return { message: "The signature did not match your wallet. Request again and sign with the connected wallet.", canRetry: true };
    case "already_requested":
    case "registration_conflict":
      return { message: "Someone already requested registration for this fixture.", canRetry: false };
    case "rate_limited":
      return { message: "Too many registration requests from this wallet today. Try again later.", canRetry: false };
    default:
      return { message: "The registration request failed. Try again in a moment.", canRetry: true };
  }
}
