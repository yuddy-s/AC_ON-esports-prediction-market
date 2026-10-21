# Milestone 3 Ethereum Sepolia deployment

Deployed on 2026-10-21 from merged commit `6e30d516669e51d7f3e4bff0d8670168da9b1f83` (PR #16). The Solidity source was clean and unchanged at deployment. [deployment.json](deployment.json) records deployment details and [guarded-buy.json](guarded-buy.json) records the subsequent live trade. The canonical backend manifest is [`deployments/sepolia-m3.json`](../../../deployments/sepolia-m3.json), with versioned ABI filenames required by the validator. Both adjacent ABI snapshots are byte-identical to those versioned exports.

| Item | Value |
|---|---|
| Chain ID | `11155111` |
| ACON | [`0x315FCA0DDAA367446f36A3184D8f6b2Df76b5618`](https://sepolia.etherscan.io/address/0x315FCA0DDAA367446f36A3184D8f6b2Df76b5618) |
| PredictionMarket | [`0x19EF739001038Ce9DFB1E12Cf45A10c9250A60a7`](https://sepolia.etherscan.io/address/0x19EF739001038Ce9DFB1E12Cf45A10c9250A60a7) |
| Market deployment/start block | `11963761` |
| Market ABI version | `PredictionMarket.6e30d516669e.792fa9f230ed.abi.json` |
| Demo market | `0`: Will Team A beat Team B? |
| Trading deadline | `1793206872` / 2026-10-28 17:01:12 UTC |
| Confirmations | `2` |
| Deployer/creator | `0xB5ce8428DD6cB9FEfD54282CB49Ef7d2629d9A6A` |

## ABI handoff

- [Versioned PredictionMarket ABI](../../../deployments/abi/PredictionMarket.6e30d516669e.792fa9f230ed.abi.json)
- [Versioned ACONTestToken ABI](../../../deployments/abi/ACONTestToken.6e30d516669e.b8482bc66b08.abi.json)
- `getMarket(uint256)` returns **six fields**: `(string question, uint256 tradingDeadline, uint8 state, address creator, uint256 yesQuantity, uint256 noQuantity)`. Retain the ID from the lookup argument or event. The proposed seventh output was reverted before deployment; Benny will discuss the identifier requirement with the team. These deployed addresses must use the six-output ABI.
- Outcomes: `YES = 0`, `NO = 1`. States: `CREATED = 0`, `OPEN = 1`, `CLOSED = 2`, `PROPOSED = 3`, `DISPUTED = 4`, `FINALIZED = 5`, `VOID = 6`.
- ACON and share quantities use `1e18` base units; deadlines use Unix seconds. ETH pays gas.
- Event names, types, and indexed fields match the approved `MarketCreated` and `TradeExecuted` schemas. The ABI includes function signatures and custom errors; [the contract README](../../README.md) documents payment, deadline, faucet, and caller-only position behavior.

## Backend configuration

For a process launched from the repository's `backend/` directory:

```dotenv
INDEXER_CHAIN_ID=11155111
PREDICTION_MARKET_ADDRESS=0x19EF739001038Ce9DFB1E12Cf45A10c9250A60a7
PREDICTION_MARKET_DEPLOYMENT_BLOCK=11963761
PREDICTION_MARKET_ABI_PATH=../deployments/abi/PredictionMarket.6e30d516669e.792fa9f230ed.abi.json
INDEXER_CONFIRMATION_DEPTH=2
```

Use the corresponding packaged/absolute ABI path in hosted deployments. Configure RPC and database credentials separately. Adriel should update the frontend address and ABI together and use the ACON address above for faucet and approval operations.

## Confirmed transactions

| Action | Transaction hash | Block |
|---|---|---:|
| Deploy ACON | `0xdf6fd63c3eace5189417448059156b4c2e9808e548d530059f0b81579377bb45` | 11963759 |
| Deploy market | `0x9ab3f9b77058f874b7817f52ab17ec99f58cb105a3c29989c984ad6a636e63a9` | 11963761 |
| Claim 1,000 ACON | `0x77dcf21dc1079af46e383ea1f18f4b39478efc210739287c6921b2dae541a3db` | 11963764 |
| Approve exact subsidy | `0xa691ae4bbd14c25a8d1c77e824991c3bb55f7249aa893bf3f446615e5925b901` | 11963765 |
| Create market 0 | `0xa4ec20ac220552ed498ce9174de1380214f67663e3d4d696de0e2b6a30b1a1a6` | 11963766 |

The creation event has log index `24`. All five receipts succeeded and their block hashes matched the canonical chain when checked. At observed head `11963773`, all were beyond the default two-confirmation depth.

## Deployment verification (before trading)

- Foundry format/build/script checks and 39 tests passed for the merged source.
- Deployed token runtime bytecode exactly matches the compiled runtime. Market runtime matches after substituting the correct ACON address at all four immutable-reference locations.
- `marketCount()` was `1`; market `0` was `OPEN`, with the recorded question/deadline/creator and zero YES/NO quantities.
- The market held exactly `34657359027997265471` ACON base units. The deployer had `965342640972002734529` base units after its faucet claim and subsidy payment, with zero remaining subsidy allowance.
- The `MarketCreated` topics and data match those reads.
- Quoting ten YES or ten NO shares initially returned `5249584441082326050` ACON base units (about 5.249584 ACON); positions were zero.

## Live guarded-buy smoke test

On 2026-10-21 at 20:02:36 UTC, the deployer bought ten YES shares in market `0` using the exact current quote as `maxCost`.

| Item | Result |
|---|---|
| Approval transaction | `0x1f4e9219f7060dff953ba262d469379236dc0fe104aebbe1cb37c4587f62e986` |
| Buy transaction | [`0xe5f5ff239ff3939cfc34c1c7719f2b1db9ef83d75f77f501236d004cb2d10c16`](https://sepolia.etherscan.io/tx/0xe5f5ff239ff3939cfc34c1c7719f2b1db9ef83d75f77f501236d004cb2d10c16) |
| Trade block / log index | `11964663` / `104` |
| YES shares received | `10000000000000000000` (10 shares) |
| Actual cost / maxCost | `5249584441082326050` (5.24958444108232605 ACON) |
| Buyer ACON afterward | `960093056530920408479` |
| Market collateral afterward | `39906943469079591521` |
| Remaining allowance | `0` |
| Approval + buy gas cost | `0.000005838084158247 ETH` |

Both receipts succeeded and were canonical. At head `11964666`, the safe checkpoint for confirmation depth two was `11964664`, beyond the trade. The on-chain position and market quantities were ten YES and zero NO, and the token balance changes matched the executed cost exactly. A subsequent quote for ten more YES shares increased to `5743819150918039250` ACON base units.

The backend's real `EthereumJsonRpcClient` and `JsonAbiLogDecoder` fetched and decoded the canonical creation and trade events with the expected fields. [guarded-buy.json](guarded-buy.json) includes the raw log and before/after checks for integration fixtures. The hosted database/indexer/API/frontend acceptance demo is still pending. The market will reject buys at or after its deadline even though its stored state remains `OPEN`.

## Gas-estimation recovery

The initial `forge script --broadcast --slow` attempt exhausted its token-creation gas limit (`593867`) at nonce `2`, transaction `0x7a51a8f1ac4416c230197f6ad0af60f71e6ea5a044330397cb8885ad746eb9bd`. No contract was created and the other four script transactions were not sent. The submitted creation bytecode matched the compiled token, but the live RPC estimated `3119274` gas for that creation.

After checking the failed receipt, empty code, and next nonce, deployment was completed at nonces `3` through `7` using `forge create` for both contracts and `cast send` for the faucet, exact subsidy approval, and market creation. Each transaction used the node's `eth_estimateGas` result with a 20% gas-limit margin. The successful market-creation deadline was calculated from the latest chain timestamp plus seven days.

Total gas paid across the failed attempt and five successful transactions was `0.000015291339514101 ETH`. After consolidating into the `Prediction Market` workspace, the local `contracts/broadcast/m3-worktree-archive/broadcast/Deploy.s.sol/11155111/run-latest.json` describes the failed script attempt, not the successful recovery. Use the transaction hashes in this record; do not resume that old script batch. The original dry-run addresses are not the final deployed pair.

The ignored `contracts/broadcast/m3-worktree-archive/` directory preserves the former M3 worktree's complete local broadcast records, caches, build artifacts, and original handoff files. The active public handoff is this `contracts/deployments/sepolia-m3-2026-10-21/` directory in the single `Prediction Market` workspace.
