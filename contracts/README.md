# Foundry contracts

The Milestone 2 Foundry project is under `contracts/`. The local Solidity source is a read-only market registry prototype: it supports creating a market and reading its question, trading deadline, state, and creator. It does not implement buying, selling, virtual credits, or collateral.

The already-deployed Ethereum Sepolia address was deployed from an earlier source version that included virtual-credit paper trading. Deployed contracts are immutable; the frontend only reads the market. A fresh deployment of the current source would be needed to have a read-only contract address on-chain.

## Local checks

Requires Foundry.

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
