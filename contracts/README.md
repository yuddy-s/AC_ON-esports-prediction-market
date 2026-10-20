# Foundry contracts

The Foundry project is under `contracts/`. `PredictionMarket.sol` remains the Milestone 2 read-only market registry prototype. `LMSR.sol` is the standalone Milestone 3 binary pricing library; integration into the registry, token transfers, positions, and guarded buys is intentionally owned by a later contract-integration change.

The LMSR library uses 18-decimal fixed point values, `b = 50e18`, and PRBMath v4.2.2 pinned as a Git submodule. It accepts at most `2_000e18` outstanding shares per outcome and `100e18` shares per transaction. Prices sum exactly to `1e18`, accepted payments telescope exactly because quote cost is `C(after) - C(before)`, and no extra buy-cost rounding buffer is applied. A positive trade whose rounded cost does not increase is rejected as too small.

The already-deployed Ethereum Sepolia address was deployed from an earlier source version that included virtual-credit paper trading. Deployed contracts are immutable; the frontend only reads the market. A fresh deployment of the current source would be needed to have a read-only contract address on-chain.

Milestone 3 trading is not implemented on this branch. The approved payment token, LMSR library boundary, public buy ABI, events, revert behavior, validation gates, and deployment handoff are documented in [`../docs/agent/interfaces/M3_TRADING_INTERFACE.md`](../docs/agent/interfaces/M3_TRADING_INTERFACE.md). Code and tests remain authoritative for which parts have actually been implemented.

## Local checks

Requires Foundry. Clone with submodules, or initialize them in an existing checkout:

```bash
git submodule update --init --recursive
```

Then run:

```bash
cd contracts
forge fmt --check
forge build
forge build script/Deploy.s.sol
forge test
```

## Ethereum Sepolia deployment

1. Copy `.env.example` to `.env` and set `SEPOLIA_PRIVATE_KEY` to a dedicated Ethereum Sepolia test wallet funded with Sepolia ETH. Keep `.env` untracked.
2. Export its variables in your shell, then deploy and seed market `#0`:

```bash
cd contracts
set -a
source .env
set +a
forge script script/Deploy.s.sol:DeployPredictionMarket \
  --rpc-url "$SEPOLIA_RPC_URL" \
  --broadcast
```

The script deploys the contract and seeds “Will Team A beat Team B?” as market `#0`, with a deadline one week after deployment. The broadcast output contains the address and transaction hashes. The Ethereum Sepolia chain ID is `11155111`.

Read market `#0` with:

```bash
cast call "$PREDICTION_MARKET_ADDRESS" \
  'getMarket(uint256)(string,uint256,uint8,address)' 0 \
  --rpc-url "$SEPOLIA_RPC_URL"
```

The deployed contract is viewable on [Sepolia Etherscan](https://sepolia.etherscan.io/address/0x5fc55783fD777BA52253E985078C3326E6ea9554).

Generate the complete frontend ABI with `forge inspect PredictionMarket abi`. The `getMarket` output order is `question`, `tradingDeadline`, `state`, `creator`; the current frontend enum order is `CREATED`, `OPEN`, `CLOSED`, `PROPOSED`, `DISPUTED`, `FINALIZED`, `VOID`.

Do not commit private keys, `.env`, `broadcast/`, or compiler output. Never deploy this demo contract to mainnet.
