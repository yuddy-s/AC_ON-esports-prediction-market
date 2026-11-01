# M4 Backend to Frontend Handoff

Status: **draft stacked PRs #30–#32**, 2026-10-30. These routes are off-chain source data and request tracking. On-chain M4 registration, market linkage, and result proposals require Benny's compiled ABI and deployment. Keep the [M3 trading interface](M3_TRADING_INTERFACE.md) as the deployed baseline.

## Fixture browsing

- `GET /api/fixtures?game_id=valorant&match_status=scheduled&limit=50&offset=0` returns `{items,total,limit,offset}`. Each item has source identity, scheduled start, status, Team A/B IDs and names, evidence URL/hash, latest result, and `authoritative:false`.
- `GET /api/fixtures/{id}` returns one item or 404. `GET /api/fixtures/{id}/results` returns append-only observations oldest first.
- The catalog ID is an off-chain integer. It is **not** Benny's `bytes32` fixture key. Organizer evidence is imported by the operator; the API does not prove source truth.

## Player-driven registration

1. With an EOA wallet on the configured chain, call `POST /api/fixtures/{id}/registration-challenges` with `{"wallet_address":"0x..."}`. The response contains `nonce`, `message`, `expires_at`, and `chain_id`. The challenge lasts five minutes. Sign the exact `message` using EIP-191 `personal_sign`; do not reconstruct its fields in the browser. It binds the fixture source identity and a SHA-256 snapshot of teams, start time, and evidence.
2. Call `POST /api/fixtures/{id}/registration-requests` with `wallet_address`, `nonce`, and the `0x` signature. A valid request returns HTTP 202 and a job. The same nonce cannot be used twice; a changed, already-resulted, or too-near fixture is rejected. Only one registration request is stored per fixture.
3. Poll `GET /api/fixtures/{id}/registration`; `null` means no request. `awaiting_abi`, `queued`, `retryable_failure`, `submitted`, and `submission_unknown` mean the player **cannot create a market yet**. `terminal_failure` needs operator resolution. Only `confirmed` means a registrar gateway matched the on-chain fixture after the configured confirmation depth. The present draft returns `awaiting_abi` and performs no chain write.
4. Once registered, the player separately signs the contract's market-creation and funding transaction. The backend never submits that user transaction. The M4 ABI and frontend contract read must establish that the fixture is still available and has no market.

The job includes `id`, `fixture_id`, `requested_by`, `chain_id`, `status`, `transaction_hash`, `error_code`, `attempts`, `next_attempt_at`, `created_at`, and `updated_at`. `transaction_hash` can be null even after an uncertain network submission; do not treat it as proof of failure. Errors return `detail:{code,message}`; stable codes include `invalid_address`, `fixture_not_found`, `fixture_ineligible`, `fixture_changed`, `invalid_challenge`, `invalid_signature`, `already_requested`, `registration_conflict`, and `rate_limited`. User-facing text should use the code and provide a way to retry a fresh challenge when appropriate.

EOA signatures are the M4 registration scope. Coinbase Smart Wallet can connect and read on Ethereum Sepolia but cannot complete Sepolia market-creation writes; use MetaMask for the end-to-end Sepolia flow. The local Anvil demo uses its development wallet. This request API does not implement EIP-1271 contract-wallet signature validation.

## Indexed market data

The M4 market, history, resolution, committee, claim, and portfolio API shapes are pending the exact event ABI. They must include chain ID, contract address, ABI version, safe block, and freshness. All indexed values are derived; frontend contract reads decide spendable positions, claimability, and whether a write is currently valid. Do not use an off-chain job status or result assessment as a settlement result.
