# Public Sepolia deployment handoff

`sepolia-m3.template.json` is an **unfilled template**, not a deployment record. It must not be used as worker configuration. After Benny deploys the exact M3 contracts, copy it to `sepolia-m3.json` and replace every placeholder with public receipt/build data. Commit the completed JSON plus both exact-build ABI files only after the team verifies them. Keep RPC URLs, database URLs, private keys, `.env`, and `contracts/broadcast/` out of Git.

## ABI version convention

Use `forge inspect PredictionMarket abi --json` and `forge inspect ACONTestToken abi --json` from the deployed source commit. Save each ABI as a JSON list under `deployments/abi/` with this filename:

```text
<ContractName>.<first 12 characters of full source commit>.<first 12 characters of ABI file SHA-256>.abi.json
```

The full SHA-256 digest goes in the manifest. The filename is the `abi_version` stored in `indexed_contracts` by the worker, so a different ABI produces a different version label. Do not rename or edit an ABI after recording its hash. The manifest uses repository-relative paths. A future incompatible manifest shape must increment `manifest_version` and update the validator and consumers together.

The market event decoder validates `MarketCreated` and `TradeExecuted` against the approved M3 field order, types, and indexed positions. `backend/app/indexer/handoff.py` additionally verifies the token/market functions needed by consumers, the manifest's chain ID, checksummed addresses, transaction hashes, block order, source commit, ABI paths, and file digests. The template deliberately fails validation until real deployment data and ABI files are supplied.

## Handoff procedure

1. Record the full deployed source commit, chain ID `11155111`, checksummed token and market addresses, and each deployment transaction hash/block from receipts.
2. Export the two ABIs from that exact source build; calculate SHA-256 for each file and use the naming convention above.
3. Record a successful market-creation transaction and a successful guarded-buy transaction, their blocks, and the demo market ID. The trade must emit `TradeExecuted`.
4. Fill `sepolia-m3.json`. From `backend/`, run `python -m scripts.validate_handoff ../deployments/sepolia-m3.json` before configuring the worker. After the API and worker are running, set `SEPOLIA_RPC_URL` privately in `backend/.env` or the process environment and run `python -m scripts.smoke_sepolia --manifest ../deployments/sepolia-m3.json --api-base-url <API_URL>`. The read-only smoke script verifies that the market's on-chain `paymentToken()` equals the manifest's ACON token address, then compares RPC chain/events, safe checkpoint, market projection, and indexed trade with the public handoff.
5. Set Render's `PREDICTION_MARKET_ADDRESS` and `PREDICTION_MARKET_DEPLOYMENT_BLOCK` from the market entry, and `INDEXER_CONFIRMATION_DEPTH` from the manifest. The manifest ABI path is relative to the repository root; when the worker starts from `backend/`, set `PREDICTION_MARKET_ABI_PATH=../<manifest market.abi_path>` and verify that file exists in the deployed filesystem. Configure `SEPOLIA_RPC_URL` and `DATABASE_URL` as private environment settings. Run one worker instance.

The [backend deployment runbook](../docs/agent/DEPLOYMENT_RUNBOOK.md) covers migrations, Render processes, and recovery. The [frontend handoff](../docs/agent/APPLICATION_ROADMAP.md#frontend-backend-api-handoff) covers mined versus indexed UI states.
