# Contract deployment and recovery runbook

Status: **local draft tooling; no M4 Sepolia deployment has been made**.
See [ABI semantics](interfaces/CONTRACT_ABI.md),
[exact generated reference](interfaces/CONTRACT_ABI_REFERENCE.md), and
[local verification](testing/CONTRACT_VERIFICATION.md). The live M3 manifest remains historical
and separate; M4 requires new token, pricing, registry and market addresses.

## 1. Establish the reviewed release inputs

- Record Matthew's M4 integer-rounding/solvency/payout approval and consumer approval of the exact
  ABI, events, fixture encoding, enums and manifest schema. Record a full source commit and build
  settings only after the reviewed code is committed. The local draft currently uses content hashes.
- Obtain the deployed **2-of-3 Sepolia Safe** with exactly Benny, Matthew and Adriel as owners.
  Confirm the three expected public addresses independently and compare them to `getOwners()`.
- Obtain Yudhveer's **distinct registrar and proposer** addresses and at least ten distinct,
  gas-funded resolver-only addresses. Resolver addresses must not be the Safe or operational keys;
  check market-specific creator/registrar/proposer/challenger/trading conflicts before each round.
  Keep wallet ownership/funding/key details in the private team runbook.
- Confirm current official Ethereum Sepolia **VRF v2.5** coordinator, keyHash/gas lane, subscription,
  callback gas limit and test-LINK funding. The Safe must already own that subscription. The consumer
  fixes coordinator/subscription/keyHash/callback gas immutably; there is no post-deployment setter.
- Populate the current deployment settings from `contracts/.env.example` in an ignored local env
  file. Keep real deployer/operational/Safe keys out of published artifacts. No browser configuration
  needs them. The deployer needs Sepolia ETH; users need the new token's faucet allocation and approvals.

The script checks chain ID, deployed Safe threshold/owner set, funded Safe-owned subscription and
constructor configuration. This is not a substitute for selecting the official coordinator and a
callback gas budget tested against the intended pool. The template's 2,000,000 callback gas is a local
starting value, not a measured live requirement. VRF uses test LINK (`nativePayment=false`), one word,
and three request confirmations.

## 2. Reproduce and simulate

From `contracts/`, load the reviewed private environment locally (for example, an ignored `.env.deploy`):

```bash
set -a
source .env.deploy
set +a
export PATH="$HOME/.foundry/bin:$PATH"
export FOUNDRY_OUT=out/current FOUNDRY_CACHE_PATH=cache/current
test "$(cast chain-id --rpc-url "$SEPOLIA_RPC_URL")" = "11155111" || exit 1
forge fmt --check
forge test
python3 script/export_handoff.py --check
forge script script/Deploy.s.sol:DeployPredictionMarket --rpc-url "$SEPOLIA_RPC_URL"
```

The final command simulates only. Review constructor inputs, gas and resulting addresses. All four
production runtime sizes must fit EIP-170. The deployment script is a local Forge harness containing
creation bytecode, not a fifth deployed production contract.

## 3. Deploy after review

With explicit deployment authorization and a successful simulation:

```bash
forge script script/Deploy.s.sol:DeployPredictionMarket \
  --rpc-url "$SEPOLIA_RPC_URL" --broadcast
```

Expected six transactions: deploy ACON, deploy pricing, deploy registry, deploy market, propose market
administration transfer to the Safe, propose registry administration transfer to the Safe. It does
not register fabricated esports fixtures, mint user balances, create markets or seed resolver wallets.

Record receipts from `broadcast/Deploy.s.sol/11155111/run-latest.json` locally. Read the market's
`paymentToken`, `pricing`, `resolverRegistry`, `vrfCoordinator`, `vrfKeyHash`, `vrfSubscriptionId`,
`vrfCallbackGasLimit`, `admin` and `pendingAdmin`; confirm them against the reviewed inputs. Verify
deployed bytecode using the exact compiler build and actual immutable values—draft runtime-template
hashes cannot be compared directly to deployed immutable-patched bytecode.

## 4. Complete the Safe batch

Set public `PREDICTION_MARKET_ADDRESS` to the receipt-derived address and `RESOLVERS` to a Solidity address
array string containing the ten or more real resolver-only addresses. Generate the CALL payloads by
local fork simulation (no broadcast flag):

```bash
forge script script/Deploy.s.sol:SafeSetupPlan \
  --sig 'calls(address,address,address,address[])' \
  "$PREDICTION_MARKET_ADDRESS" "$REGISTRAR_ADDRESS" "$PROPOSER_ADDRESS" "$RESOLVERS" \
  --rpc-url "$SEPOLIA_RPC_URL"
```

Review each returned `(to,value,data)` tuple. All are zero-value **CALL**, not DELEGATECALL. The batch:

1. Calls `acceptAdministration()` on market and registry from the Safe itself. Each acceptance
   atomically removes the previous admin; there is no later deployer-default-role renounce transaction.
2. Grants `REGISTRAR_ROLE` and `PROPOSER_ROLE` on the market to their separate keys.
3. Calls coordinator `addConsumer(subscriptionId, marketAddress)` from the subscription-owning Safe.
4. Calls registry `setResolverStatus(address,true)` for every resolver.

For ten resolvers this is 15 calls. Submit through the real Safe transaction flow with the required
two owner signatures and save the Safe/Ethereum transaction identities. The helper returns data;
it does not collect signatures or submit a Safe transaction. If setup is only partially completed,
inspect actual admins/roles/subscription/pool before constructing remaining calls. The full original
batch cannot be blindly replayed once admin acceptance has succeeded.

## 5. Verify authority and live operation

Set `FORMER_DEPLOYER_ADDRESS` to the public deployer address and simulate the verification helper:

```bash
forge script script/Deploy.s.sol:VerifyAdministration \
  --sig 'verify(address,address,address,address,address)' \
  "$PREDICTION_MARKET_ADDRESS" "$SAFE_ADDRESS" "$FORMER_DEPLOYER_ADDRESS" \
  "$REGISTRAR_ADDRESS" "$PROPOSER_ADDRESS" --rpc-url "$SEPOLIA_RPC_URL"
```

Expect `true`. It checks both Safe admins, former-deployer default-role removal, distinct operational
roles, subscription owner/LINK/consumer, and a pool of at least ten addresses without operational/admin
overlap. Also recheck the exact Safe owner addresses against the reviewed team list and check both
pending admins are zero. The helper's threshold/owner-count check alone does not identify the owners.

Focused Sepolia smoke must include:

- A real evidence-backed fixture registered by the registrar, exact fixture key/revision decode,
  one creator-funded market, and a rejected duplicate. Use truthful organizer data; local fictional
  fixtures belong only to the Anvil harness.
- New-token faucet/approval, guarded buy and sell, positions, actual token deltas and events.
- Authorized immutable proposal after trading closes, challenge bond, and a **real** coordinator
  request/callback with five distinct eligible selected addresses. Observe actual LINK spend and
  callback gas usage. The mock-only Anvil evidence cannot satisfy this check.
- Three selected resolver votes, terminal outcome, claim and duplicate-claim rejection, conservative
  remaining liabilities and creator surplus. Include bond refund/upheld behavior as applicable.
- Safe/role recovery checks and expected rejection from the former deployer/unprivileged accounts.

Use correctly pre-seeded timed markets and real block timestamps/confirmations on Sepolia. Local
Anvil covers the 24-hour, seven-day and replacement paths; time cannot be advanced on public Sepolia.
Record two-confirmed receipt/log identities for handoff/indexer use; VRF's three-confirmation request
parameter is a different setting.

## 6. Publish the real handoff

After review and successful chain checks, publish a new versioned M4 manifest (schema reviewed with
consumers) containing: chain ID `11155111`, full source commit/compiler settings, all four checksummed
addresses and deployment receipts/blocks, exact source-versioned ABI paths/SHA-256 digests, Safe and
operational roles, coordinator/subscription/keyHash/configuration, public resolver pool, role/admin/
consumer transaction receipts, confirmation depth, market/fixture IDs and example transaction/log
evidence. Retain raw public receipt fields needed for reorg-safe verification. Keep RPC URLs and keys
out of the manifest. Reuse the ABI filename convention in `deployments/README.md` with M4 contract names.

The backend's current M3 manifest validator is not an M4 validator. Yudhveer and Adriel review their
decoder/config changes against the new manifest and exact ABI. Change address, ABI, start block and
enum mapping together. Existing deployment records describe the bytecode actually on-chain;
`deployments/build.json` describes the current local build and is not live configuration.

## Recovery and operations

- **Partial deployment / gas failure:** inspect all receipts, deployed code and pending nonce before
  retrying. The M3 deployment previously underestimated live creation gas; use fresh RPC estimates with
  a reviewed margin. Blind reruns create duplicate deployments; blind `--resume` can resend incorrect
  transactions. Reconcile actual completed steps first.
- **Request failure or missing callback:** inspect emitted request-failure/pending events, pool,
  subscription consumer/LINK and request ID. A successful keeper transaction may represent a failed
  coordinator request. Retry after 30 minutes once a pool is frozen; use the existing snapshot/deadline.
  A retry invalidates the prior request even if replacement fails. At selection expiry, anyone can call
  `advanceResolution` to VOID. There is no manual randomness/committee override.
- **No quorum:** after first vote deadline advance to round 2; after second vote deadline advance to
  VOID. Preserve events and real deadline evidence. A late vote/callback cannot revive the round.
- **Operational key rotation:** Safe revokes the old narrow role and grants a distinct replacement;
  record receipts and update the signer owner's private configuration. Existing proposals and historical
  fixture-registrar conflicts remain immutable. Registry edits affect future snapshots, not selected voters.
- **Incorrect immutable configuration or terminal result:** no upgrade/admin rewrite is provided.
  Corrected source results use challenge/voting before terminal settlement. A terminal outcome cannot be
  reversed; a bad immutable deployment needs a separately reviewed replacement and new consumer config.
