# AC_ON User Guide

Status: Milestone 5 draft. Public URL and final screenshots are pending Adriel's Vercel deployment.

## What AC_ON Is

AC_ON is a Sepolia-only esports prediction market using test ACON. Team A maps to YES and Team B
maps to NO. It does not use real money. Smart contracts, not the backend or PandaScore, determine
positions, resolution, and payouts.

## Before You Start

1. Install MetaMask and create a disposable testnet-only account.
2. Select Ethereum Sepolia and obtain a small amount of Sepolia ETH for gas.
3. Open the published AC_ON URL and connect the intended account.
4. Confirm the site shows Sepolia and the expected contract before signing.
5. Claim test ACON from the application faucet if that account has not claimed before.

Never share a private key or recovery phrase. A public address is safe to share. Do not use a
wallet containing Mainnet assets for course testing.

## Fixtures And Markets

- The fixture catalog shows provider observations separately from independent operator review and
  confirmed on-chain registration.
- For an eligible reviewed fixture, sign the registration request message. This signature is free;
  the restricted registrar submits the registration transaction.
- Registration does not create a market. After confirmation, connect a funded wallet and separately
  create the market, approve the subsidy, and confirm the creation transaction.

## Trading

1. Open a market before its trading deadline and choose YES/Team A or NO/Team B.
2. Enter shares and slippage. A buy may require ACON approval followed by the buy transaction.
3. A sell requires owned shares and displays minimum proceeds after slippage.
4. Treat `Submitted`, `Mined`, and `Indexed` as different states. Mining proves the chain write;
   indexing only means the derived backend/UI has caught up after confirmations.

## Results, Challenges, And Resolvers

- The proposer may submit an independently reviewed YES, NO, or VOID result after trading closes.
- A non-proposer may challenge during the displayed window by approving and posting the 10 ACON bond.
- Chainlink VRF selects five eligible resolver addresses. Only selected resolver wallets may vote.
- Three matching YES, NO, or VOID votes settle the dispute. A failed round may use one replacement;
  exhausted resolution paths end in VOID according to the contract.

## Claims And Portfolio

- The portfolio reads positions and claimability directly from the contract; the indexed backend
  provides trade history and derived metadata.
- After FINALIZED, winning shares pay one ACON each. After VOID, one combined claim pays
  `floor((YES shares + NO shares) / 2)` ACON base units.
- Confirm the claim once. Duplicate claims are rejected by the contract.
- Market creators may withdraw only surplus above conservative remaining liabilities.

## Common Problems

| Problem | What to check |
|---|---|
| Wrong network | Select Ethereum Sepolia in MetaMask and reload. |
| Not enough gas | Fund the disposable wallet with Sepolia ETH. |
| Not enough ACON | Claim once from the faucet or reduce the transaction. |
| Fixture cannot be registered | Confirm it is independently reviewed, scheduled, unchanged, and not too close to start. |
| Mined but not indexed | Wait for two confirmations; the chain state remains authoritative. |
| Indexer/API unavailable | Do not resubmit a successful transaction. Check its Etherscan receipt first. |
| Cannot challenge | Confirm the proposal window is open, this wallet is not the proposer, and it has 10 ACON. |
| Cannot vote | Only the five selected resolver addresses can vote, once per round. |

## Evidence And Support

For course testing, record only public URLs, public wallet addresses, transaction hashes, blocks,
and sanitized screenshots. Report reproducible defects using the M5 defect template; never attach
private keys, tokens, database/RPC URLs, or recovery phrases.
