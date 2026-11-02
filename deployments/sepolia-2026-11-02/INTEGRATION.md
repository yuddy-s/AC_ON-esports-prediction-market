# M4 integration handoff

The Sepolia deployment and Safe permission setup are complete. Use
[manifest.post-setup.json](manifest.post-setup.json) as the latest recorded configuration.
The initial `manifest.json` is an immutable pre-setup snapshot.

Safe execution:
[`0x89d8949a8cfaa91bfbd44345d8830470a5ddfbc001e346907ad4ec8f964ff69e`](https://sepolia.etherscan.io/tx/0x89d8949a8cfaa91bfbd44345d8830470a5ddfbc001e346907ad4ec8f964ff69e),
block **12051344**. All 15 inner calls and the resulting permissions were verified.
At verification block **12051383**, the market count and VRF request count were both zero.

## Yudhveer: backend and operational signing

The authorized service accounts are:

| Role | Address |
|---|---|
| Registrar | `0xFfb7c2D7B39A3da503Ef30761CCD1B19B767eDaa` |
| Proposer | `0x137F79Cc7eA5c59Fa66bc09351b5f9331225c0Df` |

Both roles are granted on PredictionMarket. Configure the corresponding signer accounts in the
backend's private operational environment. The Safe owner keys are not service signers.

Public M4 configuration values, with paths relative to a worker launched from `backend/`:

```dotenv
INDEXER_CHAIN_ID=11155111
PREDICTION_MARKET_ADDRESS=0x03ae48f03C7822540a91DA2168602bd49dC510E9
PREDICTION_MARKET_DEPLOYMENT_BLOCK=12051223
INDEXER_CONFIRMATION_DEPTH=2
PREDICTION_MARKET_ABI_PATH=../deployments/abi/PredictionMarket.721a6fef039a.4af9297937eb.abi.json
```

The start block covering all four deployments is **12051217**; the value above is the market's
own creation block for a market-only log filter. Keep the RPC and database configuration private.

**Implementation work remains in the checked-out `721a6fe` baseline:**

- `backend/app/indexer/worker.py` constructs the strict M3 `JsonAbiLogDecoder`.
  `backend/app/indexer/decoder.py` requires the old `MarketCreated` shape, so pointing that worker
  at this M4 ABI is not sufficient. Integrate the M4 event mapping/projections and their tests.
- Registrar/proposer gateways are still mocks in this baseline. Connect the reviewed signing
  gateways, durable transaction tracking, confirmations, and matching chain-state checks before
  reporting an operation as confirmed.
- Review the M4 manifest schema and wire fixture linkage, resolution/committee, claims, and
  portfolio APIs. The existing M3 manifest validator/smoke command does not validate this handoff.
- Rebuild/backfill the intended M4 projections with the matching address, ABI, and deployment block.
  Keep historical M3 data paired with its original contract and ABI.

These notes describe the checked-out baseline, not any unpublished work on a teammate's branch.

## Adriel: frontend and wallet configuration

Use the M4 public values in the frontend's local configuration:

```dotenv
VITE_CHAIN=sepolia
VITE_PREDICTION_MARKET_ADDRESS=0x03ae48f03C7822540a91DA2168602bd49dC510E9
VITE_ACON_TOKEN_ADDRESS=0xf85b2278a810410c6AE0b7490d34671E0C8e6E90
VITE_API_URL=http://localhost:8000
```

The checked-out `frontend/.env.example` still contains the historical M3 addresses. Pair these
new addresses with the M4 ABI and the intended M4 backend. Use the real API host if it differs from
the local URL above. A market ID is available only after a successful market-creation receipt.

Verify fixture registration status before showing market creation. Preserve submitted, mined,
and indexed states, and decode the full lifecycle, resolver selection, votes, and claims.
Private signer keys belong only in wallet/backend secret storage, never in `VITE_*` variables.

## Benny and team: live transaction acceptance

1. Select a real upcoming fixture with organizer evidence, reviewed Team A/YES and Team B/NO
   mapping, and valid scheduling. The registrar records it on-chain; record the fixture key,
   revision hash, receipt, and block.
2. Use a separate user account to claim the new token's faucet allocation, approve collateral,
   and create/fund the market. The backend does not create or fund the user's market.
3. Exercise guarded buy/sell and reconcile receipts, token/share balances, indexer projections,
   and API/frontend reads.
4. After trading closes and a reviewed result is available, have the authorized proposer submit
   the evidence-backed outcome. Exercise the bonded challenge and explicit resolver-selection
   request using appropriately separate accounts.
5. Observe a **real Chainlink request and fulfillment**, record request ID, five selected resolvers,
   callback receipt, LINK spend, and gas usage. Ten resolver-only wallets are active and funded.
6. Obtain three matching votes from selected resolvers, verify settlement, claim payouts, and
   check duplicate-claim rejection and collateral/bond reconciliation.

Use live RPC gas estimates: the deployment exposed a substantial difference between the pinned
local Cancun gas accounting and current Sepolia state-creation costs. Public Sepolia deadlines
must elapse normally. Keep resolver-only accounts out of market creation, trading, and challenges
for markets they may resolve.

The read-only callback gas probe and the earlier mock-Anvil journeys are useful verification
evidence, but they do not replace the real VRF and whole-application acceptance receipts.
