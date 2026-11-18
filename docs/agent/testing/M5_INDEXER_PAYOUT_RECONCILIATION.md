# M5 Indexer Payout Reconciliation

The payout projection now removes the claimed YES and NO shares from the indexed market's
outstanding quantities and records the claim block on the wallet position. Previously,
`PayoutClaimed` cleared the wallet's positions but left the market quantities and the position's
`updated_block_number` stale. The on-chain claim was correct; the derived read model disagreed.
This is the local accounting defect tracked as ECON-B1 in Matthew's M5 supplement and relates
to [issue #56](https://github.com/yuddy-s/AC_ON-esports-prediction-market/issues/56).

## Change and Regression Coverage

`backend/app/indexer/service.py` subtracts the event's `yes_shares` and `no_shares` from the
market quantities, then clears both wallet positions and updates their block number. The
existing processed-log tracking keeps repeated synchronization idempotent. The database schema
and contract interface are unchanged.

`backend/tests/test_m4_indexer.py` checks:

- A winning claim consumes the remaining market quantity and updates the wallet's block.
- A VOID claim consumes both sides while preserving another wallet's outstanding shares.
- A second wallet's claim leaves both market quantities at zero.
- Repeated synchronization does not subtract the shares twice.
- A full projection rebuild reproduces the quantities, claim state and position block.

From `backend/`, with the project's Python environment activated:

```bash
DATABASE_URL=sqlite+pysqlite:////tmp/acon-indexer-tests.sqlite python -m pytest -q tests/test_m4_indexer.py
DATABASE_URL=sqlite+pysqlite:////tmp/acon-backend-tests.sqlite python -m pytest -q
```

The local SQLite validation passes 3 focused tests and 130 backend tests. It does not establish
shared Supabase, deployed API or hosted frontend agreement.

## Existing Sepolia Receipt Evidence

The November 17 2026 ET observations for market 0 on contract
`0x03ae48f03C7822540a91DA2168602bd49dC510E9` provide the comparison target:

| Action | Receipt block | Recorded result |
|---|---:|---|
| [VOID settlement and bond refund](https://sepolia.etherscan.io/tx/0x569d65ff15925d37ff0dabd00a8033e708a923fa68de8dd1e0cceef6cbcb4dcb) | 12158923 | 10 ACON bond refunded; remaining liability 125.0055 ACON |
| [Payout](https://sepolia.etherscan.io/tx/0xc7d625cf7ddb708977c3c1e44cb6f4d23a650915a041d9ac393754cb8e5fa5f9) | 12158940 | 125.0055 ACON paid; both quantities and positions zero; claimed flag true |
| [Creator surplus](https://sepolia.etherscan.io/tx/0xe4f7b7e1c8e241007fa0bf435ccd5e48e303af4c67dba2abd5f084312b1eae13) | 12158955 | 40.665164062370061911 ACON withdrawn; collateral and liability zero |

Saved observations:
[settlement](../../../deployments/sepolia-2026-11-02/market-0-void-settlement-evidence.json),
[payout](../../../deployments/sepolia-2026-11-02/market-0-void-payout-evidence.json),
[surplus](../../../deployments/sepolia-2026-11-02/market-0-creator-surplus-evidence.json), and
[backend verification status](../../../deployments/sepolia-2026-11-02/market-0-backend-indexer-verification.json).
These records are historical receipt checks, not a new shared-database verification.

## Deploy and Repair Existing Projections

Deploying this handler corrects newly processed claims. It does not revisit claims that are
already behind the indexer checkpoint. The deployment owner must replay the affected deployment.

1. Obtain working shared database access. Record the migration revision, checkpoint and a backup
   of the affected deployment's projections. Pause the running indexer during the rebuild.
2. Deploy the corrected backend. Confirm the configured chain, contract, deployment block and
   exact ABI match the deployment being repaired. Use an RPC endpoint that serves its history.
3. From `backend/` with the reviewed deployment environment loaded, run:

   ```bash
   python -m app.indexer.worker --rebuild
   ```

   This existing command clears derived market, trade, position, event and processed-log rows
   for the configured chain and contract, resets that deployment's checkpoint, and rebuilds
   from its deployment block. It does not submit wallet transactions.
4. Resume the polling indexer. Verify its safe checkpoint has reached at least block 12158955
   for this recorded market 0 journey and that the indexer is fresh.
5. Compare the database, `/api/v2` responses and hosted frontend with the receipt hashes and
   quantities above. Confirm the claimed flag, exact payout and surplus amounts, zero remaining
   YES/NO quantities, zero wallet positions and zero outstanding liability.

Shared verification was blocked when the supplied Supabase connection failed with
`tenant/user not found`. ECON-05 and the full PUB-09/PUB-10 cross-layer acceptance rows remain
blocked until that environment passes. This fix does not complete the real VRF, committee,
voting or settlement demonstration required by issue #56.
