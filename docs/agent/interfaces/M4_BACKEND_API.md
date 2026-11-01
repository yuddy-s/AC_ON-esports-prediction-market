# M4 Backend to Frontend Handoff

Provider status: PR #39 merged the optional, gated PandaScore adapter and operator review path. PandaScore fixtures and result observations remain non-authoritative. A provider result is not an on-chain proposal; a future proposer gateway may use an assessment only after independent evidence is attached to that exact observation. The UI should show the source and update time, never infer settlement or claimability from provider data.

PandaScore listings return `detail.code=fixture_unreviewed` (HTTP 409) from the registration challenge route until an operator approves that specific fixture with independent evidence. Approval is bound to the team mapping and scheduled start and is revoked by a change to either. It is an off-chain selection, not an on-chain registration or permission to create a market.

Catalog and detail items include `registration_eligible` as a current off-chain precheck for scheduled start, teams, result absence, and curation. It can change between reads; a signed challenge is still required and `registration_request_status=confirmed` remains the separate on-chain gate before market creation.

Status, **2026-11-01:** PRs #30–#34 and #39 are merged. The fixture catalog, signed registration requests, recovery audit, result assessments/reviews, and optional PandaScore adapter are implemented off-chain. They do not submit registrar or proposer transactions. PR #37 is open with candidate ABI artifacts; exact ABI freeze and deployment handoff remain pending. Keep the [M3 trading interface](M3_TRADING_INTERFACE.md) as the deployed baseline.

## Fixture browsing

- `GET /api/fixtures?game_id=valorant&match_status=scheduled&limit=50&offset=0` returns `{items,total,limit,offset}`. Each item has source identity, scheduled start, status, Team A/B IDs and names, evidence URL/hash, latest result, nullable `registration_request_status`, and `authoritative:false`. That status describes the backend job, not independent chain proof.
- `GET /api/fixtures/{id}` returns one item or 404. `GET /api/fixtures/{id}/results` returns append-only observations oldest first.
- The catalog ID is an off-chain integer. It is **not** Benny's `bytes32` fixture key. Organizer evidence is imported by the operator; the API does not prove source truth.

## Player-driven registration

1. With an EOA wallet on the configured chain, call `POST /api/fixtures/{id}/registration-challenges` with `{"wallet_address":"0x..."}`. The response contains `nonce`, `message`, `expires_at`, and `chain_id`. The challenge lasts five minutes. Sign the exact `message` using EIP-191 `personal_sign`; do not reconstruct its fields in the browser. It binds the fixture source identity and a SHA-256 snapshot of teams, start time, and evidence.
2. Call `POST /api/fixtures/{id}/registration-requests` with `wallet_address`, `nonce`, and the `0x` signature. A valid request returns HTTP 202 and a job. The same nonce cannot be used twice; a changed, already-resulted, or too-near fixture is rejected. Only one active job is stored per fixture. After certain terminal failures, a fresh signed challenge may reauthorize that job while its earlier audit remains intact; submitted/uncertain/confirmed jobs cannot be replaced.
3. Poll `GET /api/fixtures/{id}/registration`; `null` means no request. `awaiting_abi`, `queued`, `retryable_failure`, `submitted`, and `submission_unknown` mean the player **cannot create a market yet**. `terminal_failure` needs operator resolution. Only `confirmed` means a registrar gateway matched the on-chain fixture after the configured confirmation depth. The current implementation has no production chain gateway and does not confirm registrations on-chain.
4. Once registered, the player separately signs the contract's market-creation and funding transaction. The backend never submits that user transaction. The M4 ABI and frontend contract read must establish that the fixture is still available and has no market.

The job includes `id`, `fixture_id`, `requested_by`, `chain_id`, `status`, `transaction_hash`, `error_code`, `attempts`, `next_attempt_at`, `created_at`, and `updated_at`. `transaction_hash` can be null even after an uncertain network submission; do not treat it as proof of failure. Errors return `detail:{code,message}`; stable codes include `invalid_address`, `fixture_not_found`, `fixture_ineligible`, `fixture_changed`, `invalid_challenge`, `invalid_signature`, `already_requested`, `registration_conflict`, and `rate_limited`. User-facing text should use the code and provide a way to retry a fresh challenge when appropriate.

EOA signatures are the M4 registration scope. Coinbase Smart Wallet can connect and read on Ethereum Sepolia but cannot complete Sepolia market-creation writes; use MetaMask for the end-to-end Sepolia flow. The local Anvil demo uses its development wallet. This request API does not implement EIP-1271 contract-wallet signature validation.

## Indexed market data

`GET /api/indexer/status` includes nullable `abi_version` alongside chain, contract, safe block, and freshness; compare all of them to the selected deployment. The current decoder handles the M3 `MarketCreated` and `TradeExecuted` events. M4 event projections and M4 market/history/resolution/committee/claims/portfolio APIs are pending the reviewed ABI and implementation. The planned M4 read surface uses `/api/v2` to keep M3 route behavior stable. Indexed values are derived; frontend contract reads decide spendable positions, claimability, and whether a write is currently valid. Do not use an off-chain job status or result assessment as a settlement result.

### Planned M4 read routes (not implemented)

- `GET /api/v2/indexer/status` reports the indexed M4 chain, contract, ABI version, latest/safe block, lag, and status freshness.
- `GET /api/v2/markets` and `GET /api/v2/markets/{market_id}` expose indexed M4 markets and deployment metadata.
- `GET /api/v2/markets/{market_id}/history` returns confirmed buy and sell activity in chain order.
- `GET /api/v2/markets/{market_id}/resolution` returns derived proposal, challenge, resolver-round, committee, vote, and final-outcome history.
- `GET /api/v2/markets/{market_id}/claims` returns indexed payout and creator-surplus events.
- `GET /api/v2/portfolio/{wallet_address}` returns derived market positions and activity. It does not replace contract reads for current balances or claimable amounts.
- Existing `GET /api/fixtures/{id}` and catalog reads gain nullable confirmed on-chain registration and linked-market information after the M4 `FixtureRegistered` and `MarketCreated` projections exist. Existing `registration_request_status` continues to describe the off-chain job only.

Every M4 indexed response is derived and carries chain, contract, ABI version, and safe-block/freshness metadata. The paths are scoped to the configured M4 deployment; exact response fields must follow the frozen ABI and frontend review. These routes do not submit transactions.
