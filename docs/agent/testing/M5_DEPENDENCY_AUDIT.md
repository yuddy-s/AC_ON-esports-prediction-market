# M5 Frontend Dependency Audit (Issue #54)

Owner: Adriel. Baseline captured November 18, 2026 with `npm audit --omit=dev` on the frontend
lockfile of `feature/m5-vercel-playwright` (wagmi 2.19.5, viem 2.56.9). Registry results change over
time; rerun the command before relying on these counts. Package counts are not confirmed
vulnerabilities in AC_ON.

## Baseline

| Date | Lockfile | Total | Critical | High | Moderate | Source |
|---|---|---|---|---|---|---|
| 2026-11-08 | `main` before PR #51 | 29 | 0 | 17 | 12 | Issue #54 |
| 2026-11-18 | `dev` after PR #51 (non-breaking lockfile updates) | 27 | 0 | 16 | 11 | This audit |
| 2026-11-18 | `npm audit fix` without `--force` (dry run) | 27 | 0 | 16 | 11 | No further non-breaking fixes exist. |
| 2026-11-18 | wagmi 3.7.11 + `npm audit fix` (branch `chore/m5-wagmi3-upgrade`) | 0 | 0 | 0 | 0 | This audit |

## Root Advisories And Reachability

The 27 packages trace back to six advisories in four libraries. The rest are packages that only
depend on them (WalletConnect, Reown AppKit, MetaMask SDK, Gemini wallet, Coinbase CDP SDK, viem,
wagmi). Reachability was checked against the production bundle (`npm run build`, `dist/assets/*.js`).

| Advisory | Library and range | Impact | How it enters | In the shipped bundle? | Reachable in AC_ON? |
|---|---|---|---|---|---|
| [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5) (high) | zod < 4.6.6 | Memory exhaustion validating oversized constrained collections | `abitype/zod` subpath; Coinbase CDP SDK; Reown | No: no zod code or `ZodError` in the bundle | No. viem does not import `abitype/zod`, and the app validates nothing with zod. |
| [GHSA-qr28-fpjm-wq7f](https://github.com/advisories/GHSA-qr28-fpjm-wq7f) (high), [GHSA-vcc3-ghjq-m6fr](https://github.com/advisories/GHSA-vcc3-ghjq-m6fr) (moderate) | decode-uri-component ≤ 0.5.0 | Denial of service on malformed percent-encoded input | `query-string` in WalletConnect utils | No: no `query-string` or `decode-uri-component` code | No. AC_ON enables only the Coinbase and injected (MetaMask) connectors; WalletConnect is never imported. |
| [GHSA-96hv-2xvq-fx4p](https://github.com/advisories/GHSA-96hv-2xvq-fx4p) (high), [GHSA-58qx-3vcg-4xpx](https://github.com/advisories/GHSA-58qx-3vcg-4xpx) (moderate) | ws 8.x below 8.21.0 (nested 8.18.0 and 7.5.13 copies) | Memory disclosure or exhaustion in a Node WebSocket server/client | viem `isows`, Solana and WalletConnect packages | No: the only WebSocket code is the Coinbase SDK, which uses the browser's built-in `WebSocket` | No. `ws` is a Node library; browsers use the native WebSocket, and AC_ON reads over HTTP only. |
| [GHSA-w5hq-g745-h8pq](https://github.com/advisories/GHSA-w5hq-g745-h8pq) (moderate) | uuid < 11.1.1 | Missing buffer bounds check in v3/v5/v6 when a buffer is passed | MetaMask utils (via MetaMask SDK and Gemini) | No: "uuid" appears only as object property names; IDs come from `crypto.randomUUID` | No. The MetaMask SDK and Gemini connectors are not imported. |

**Result:** no root advisory is reachable in the browser paths AC_ON enables. All six are denial of
service or memory issues in Node-side or unused connector code, not key or transaction compromise.

## Mitigations Already In Place

- Only two connectors are configured (`frontend/src/wagmi.ts`): Coinbase Smart Wallet and the
  injected browser wallet. Unused connector SDKs are tree-shaken out of the build.
- The browser holds no secrets (`VITE_*` values are public), and every write is signed in the
  user's wallet, which shows the contract call before signing.
- Reads use HTTP JSON-RPC only, with a fallback across public endpoints (M5-004).
- Vercel serves `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` and a strict referrer
  policy.

## wagmi 3 Evaluation (Isolated Branch)

Branch `chore/m5-wagmi3-upgrade`, with merged PR #60 and current `dev` incorporated at
`432db05`. Automated checks were rerun on `64bc4a1`; the later changes are documentation only.

| Check | Result |
|---|---|
| Code change | `wagmi` ^2.12.17 → ^3.7.11; one source change: `coinbaseWallet({ preference: { options: "smartWalletOnly" } })` (the option became an object). viem unchanged (2.56.9). |
| `npm audit --omit=dev` | 0 vulnerabilities (after `npm audit fix`, which moved the Coinbase wallet SDK's zod to 4.6.7) |
| `npm run typecheck` | clean |
| `npm test` | 183 passed on the current branch (163 in the initial isolated evaluation) |
| `npm run build` | succeeded |
| `npm run test:e2e` (local build, Sepolia) | Initial isolated evaluation: 14/14, twice. The current corrected suite discovers 24 tests; Matthew did not rerun the full browser suite during this review. |
| Manual MetaMask smoke on Sepolia (connect, faucet, approve + buy, sell, network switch) | **pass with the FE-B3 refresh workaround**, November 19 on `432db05`; [manual results and receipts](M5_FRONTEND_RESULTS.md#manual-wallet-smoke-wagmi-3-pr-63) |
| Coinbase Smart Wallet connect popup | **pass**, November 19 on `432db05`: popup opened and connected; Sepolia writes were not attempted |

## Decision

- **Adopt wagmi 3** through PR #63 after approval and passing checks. PR #60 is merged, and the
  manual MetaMask and Coinbase connection checks are complete. The successful approve/buy smoke
  required the documented FE-B3 refresh workaround once.
- **Deployment:** the upgrade reaches the public site only after deployment from the merged `dev`.
  The local manual smoke does not complete hosted wallet verification for ECON-05.
- **Follow-up:** FE-B3 remains open, owned by Adriel. Its cause and relationship to the upgrade
  are unconfirmed; the workaround is a page refresh after the approval. See the defect log.

**Smoke result (November 19, 2026, commit `432db05`): pass.** MetaMask connection, wrong-network
switching, faucet claim, approve + buy and sell all succeeded on Sepolia, and the Coinbase Smart Wallet
popup opened and connected. Receipts are in
[M5_FRONTEND_RESULTS.md](M5_FRONTEND_RESULTS.md#manual-wallet-smoke-wagmi-3-pr-63). `npm audit
--omit=dev` on this commit reports 0 vulnerabilities. One recoverable defect (M5-006: a refresh was
needed once after the buy approval) is logged with a planned follow-up; it is not specific to the
upgrade as far as is known. wagmi 3 is ready to adopt once PR #63 is approved; the public site stays
on wagmi 2 until it is redeployed from `dev` after the merge.

## Keeping This Current

- Rerun `cd frontend && npm audit --omit=dev` before each milestone and update the baseline table.
- No new critical advisories are accepted. A new high advisory needs a reachability row before the
  next deployment.
- Report counts as "packages flagged by npm audit", not as confirmed vulnerabilities.
