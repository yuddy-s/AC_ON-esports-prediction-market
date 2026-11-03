import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createRegistrationChallenge,
  describeRegistrationError,
  RegistrationApiError,
  submitRegistrationRequest,
} from "./registrationApi";

function respond(status: number, body: unknown) {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body), { status })));
}

afterEach(() => vi.unstubAllGlobals());

describe("registration requests", () => {
  const wallet = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8";

  it("posts the wallet address for a challenge", async () => {
    respond(201, { nonce: "n1", message: "Sign this", expires_at: "2026-11-01T00:05:00Z", chain_id: 31337 });
    const challenge = await createRegistrationChallenge(3, wallet);
    expect(challenge.message).toBe("Sign this");
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toMatch(/\/api\/fixtures\/3\/registration-challenges$/);
    expect(JSON.parse(String(init?.body))).toEqual({ wallet_address: wallet });
  });

  it("turns a backend rejection into its stable error code", async () => {
    respond(409, { detail: { code: "already_requested", message: "Fixture registration has already been requested" } });
    const error = await submitRegistrationRequest(3, wallet, "n1", "0xsig").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(RegistrationApiError);
    expect(error).toMatchObject({ code: "already_requested", status: 409 });
  });

  it("still fails clearly when the error body is not the documented shape", async () => {
    respond(500, "Internal Server Error");
    const error = await submitRegistrationRequest(3, wallet, "n1", "0xsig").catch((e: unknown) => e);
    expect(error).toMatchObject({ code: "http_error", status: 500 });
  });
});

describe("describeRegistrationError", () => {
  it("offers a retry when a fresh signature can fix it", () => {
    expect(describeRegistrationError("invalid_challenge").canRetry).toBe(true);
    expect(describeRegistrationError("fixture_changed").canRetry).toBe(true);
  });

  it("does not offer a retry when the fixture is taken or the wallet is limited", () => {
    expect(describeRegistrationError("already_requested").canRetry).toBe(false);
    expect(describeRegistrationError("rate_limited").canRetry).toBe(false);
  });

  it("has a fallback for unknown codes", () => {
    expect(describeRegistrationError("something_new").message).toMatch(/failed/);
  });
});
