# Milestone 4 Feature-Complete Design Decision

> **Provider amendment implemented but gated:** PR #39 merged the PandaScore fixture/result adapter and independent-review workflow. Live ingestion remains disabled until written permission and team approval confirm this educational test-token use. PandaScore responses alone are not independent organizer evidence and cannot trigger automatic proposals.

Status: **target design approved and merged in PR #28 on 2026-10-29; locally verified contract and backend slices are available for final integration**. Matthew's economic proof/invariants are included in PR #37's combined contract head, whose [exact-build ABI](CONTRACT_ABI.md), event fixtures, verification record, and deployment tooling are under final consumer review. PRs #30–#34 and #39 provide the off-chain catalog and guarded registrar/proposer workflows. None of this is a deployed M4 release: fresh Sepolia deployment, role/VRF handoff, frontend/backend contract integration, and cross-layer acceptance remain required. The [M3 interface](M3_TRADING_INTERFACE.md) describes the historical live baseline.

## Fixture and result source

The required no-cost boundary includes a deterministic repository-owned mock and a manual JSON fixture/result adapter. Each normalized record contains provider ID, game ID, external match ID, scheduled start, match status, Team A/B IDs and names, winner when available, source update time, and organizer evidence URL/hash. A PandaScore free adapter is optional and disabled until written permission confirms this educational test-token prediction use; no paid esports-data plan is required for M4. Source data assists the proposer but never settles a market. Proposals are immutable; conflicting or corrected results use challenge and resolver voting. Finalized outcomes cannot be reversed in M4.

Only a restricted registrar registers a selected fixture on-chain. Its key is `keccak256(abi.encode(providerId, gameId, externalMatchId))`. YES is Team A; NO is Team B. Provider, team IDs/order, and scheduled start cannot change after market creation. Exactly one user-funded market may exist per fixture. Its trading deadline must be at least 15 minutes before the registered start. The registrar may close trading early with an evidence hash when play starts early, but cannot extend or reopen it. A postponement is fixture metadata and does not reopen trading. Canceled, tied, no-contest, or unsupported results are proposed as VOID and receive the same challenge period. If seven days pass after the trading deadline without a proposal, anyone can start resolver selection. The registry blocks unregistered fixture IDs; it cannot prove the registrar or source is truthful.

## Trading, proposal, and settlement

`quoteBuy` returns the certified mathematical ceiling of the LMSR cost increase and
`quoteSell(marketId, outcome, shares)` returns the certified mathematical floor of the cost
decrease. `sell(marketId, outcome, shares, minReturn)` requires owned shares, at most `100e18`
shares per trade, stored `OPEN` state, and `block.timestamp < tradingDeadline`; it reverts when
proceeds fall below `minReturn`. The frontend derives `minReturn` from user slippage. Under a
reentrancy guard, accounting and positions update before ACON transfers. Successful rounding
leaves a nonnegative residue in collateral rather than an exact rounded-potential equality. The
regression vector and solvency inequality are recorded in the
[M4 economic proof](../testing/M4_ECONOMIC_PROOF.md).

**Local rounding correction under final review:** the current draft preserves the mathematical
floor for sells and changes executable buy amounts to the mathematical ceiling of the cost
increase. Benny authorized the paired correction to prevent reverse-trade gains from mixing
strict-floor sells with the previous rounded-potential buys. The updated proof and invariants now
use this rule; the numeric amendment and interval error behavior still require reviewer/consumer
approval and are not retroactive PR #28 approval. See
[the pricing review record](../testing/PRICING_ROUNDING.md).

An authorized proposer submits YES, NO, or VOID with evidence hash and reference after trading closes. One immutable proposal opens a fixed 24-hour challenge window. Any address except its proposer may submit the first challenge with a 10 ACON bond; subsequent challenges revert. If the final outcome differs, including YES/NO becoming VOID, refund the challenger; if upheld, forfeit the bond to market collateral, available as creator surplus only after claims are reserved. Anyone may finalize an unchallenged proposal after the window. A challenged proposal proceeds to resolver selection. The seven-day no-proposal path also proceeds to resolver selection.

The **stored** M4 market-state enum, in order, is `OPEN`, `CLOSED`, `PROPOSED`, `DISPUTED`, `RESOLVER_SELECTION`, `RESOLVER_VOTING`, `FINALIZED`, `VOID`. Resolver round 1 or 2 is stored separately. `CLAIMABLE` is a derived read from terminal state, position, and claimed status; `POSTPONED` and `ORACLE_TIMEOUT` are not market states. Expired transitions require an on-chain caller; time passing does not mutate storage.

Final YES/NO pays 1 ACON per outstanding winning share. VOID pays 0.5 ACON per outstanding YES and NO share. A wallet claims once per market; a VOID claim combines both holdings. Mark claimed, clear/decrement positions and liabilities, and update collateral before token transfer; duplicate claims revert. Winning liability equals outstanding winning quantity; VOID reserves `ceil((outstandingYes + outstandingNo) / 2)` base units. Challenge bonds remain separate until disposition. Creator surplus can be withdrawn only in `FINALIZED` or `VOID`, only above conservative remaining liabilities. No fees. Matthew's rounded-ledger collateral proof and payout review are mandatory before payout code merges.

## Resolver selection and voting

An on-chain allowlist should have at least ten resolver-only Sepolia addresses. Five **distinct** eligible addresses form each committee using one random word from a Chainlink VRF v2.5 subscription, billed in Sepolia test LINK, with three block request confirmations. Each selection round snapshots eligible addresses and has a fixed seven-day deadline. A failed request can be retried after 30 minutes using the same snapshot and deadline. Only the current request ID can install a committee; superseded, duplicate, mismatched, or late fulfillments emit `VRFFulfillmentIgnored` without changing state. Anyone may trigger expired transitions.

Each selected wallet sends one direct YES, NO, or VOID vote during a 48-hour voting period. Three YES or NO votes lead to `FINALIZED`; three VOID votes lead to `VOID`. If round 1 has no quorum, open exactly one replacement round with a new candidate snapshot. Exclude first-round resolvers if at least five other eligible addresses exist; otherwise eligible first-round addresses may be reused. Failure to form either committee by its deadline or failure to reach quorum in round 2 leads to `VOID`. Both terminal states expose the relevant claim read/action. Relayed voting and EIP-1271 signature recovery are outside M4.

Exclude the creator, fixture registrar for that fixture, proposer, challenger, anyone who bought or sold in that market, current position holders, the resolver-admin address, and duplicates within a committee. Checks are address-level only; undisclosed related wallets cannot be detected. Ten addresses controlled by four teammates provide address-level separation, not ten independent human decision makers.

## Roles, events, and ABI handoff

Benny deploys and grants roles, then transfers administration and renounces/loses direct default-admin power. A 2-of-3 Sepolia Safe controlled by Benny, Matthew, and Adriel owns resolver-registry administration, role recovery, and the VRF subscription. The Safe grants Yudhveer's separate registrar and proposer keys narrow roles. Yudhveer owns provider token, RPC, DB, Render and oracle secrets, audit log, and key-rotation instructions. Adriel owns frontend deployment and public config, with no private key or provider token in browser/Vercel public variables. Hosted secrets stay in service secret stores; local secrets stay in ignored `.env` files. Revoke and replace exposed operational keys. Safe signer keys are never hosted. Resolver-wallet ownership/funding belongs in a private team runbook.

Required event names: `FixtureRegistered`, `MarketCreated`, `TradeExecuted`, `SellExecuted`, `MarketClosed`, `OutcomeProposed`, `OutcomeChallenged`, `ResolverSelectionRequested`, `ResolverCommitteeSelected`, `VRFFulfillmentIgnored`, `ResolverVoteCast`, `MarketFinalized`, `MarketVoided`, `PayoutClaimed`, `CreatorSurplusWithdrawn`. Required reads: fixture and market lookup, `quoteBuy`, `quoteSell`, position balance, proposal/challenge details, current round/committee, vote tallies, claimable amount, claimed flag, and withdrawable surplus. **Event names are design categories, not a compiled ABI.** Benny and consumers must freeze exact Solidity argument types, indexed positions, read signatures, numeric units, and error behavior in an ABI table before dependent implementation; do not invent signatures from this list. Publish the exact compiled ABI and a versioned manifest with source commit, chain ID, token/market addresses, deployment block, ABI digest, roles, and example transactions.

The frontend signs user writes and uses contract reads for spendable/claimable amounts. The backend does not submit user trades, challenges, votes, or claims. The indexer projects confirmed logs with unique identity, checkpoints, and reorg repair; FastAPI exposes derived history/freshness. PostgreSQL never selects resolvers or settles outcomes.

## Release scope and implementation gates

M4 acceptance requires all planned features, complete normal/disputed/timeout/VOID/claim journeys on local Anvil, component tests and a documented full test plan, matching ABI/design docs, and a new Sepolia contract deployment with focused transaction smoke tests. Public Vercel/Render/Supabase/Sepolia integration is an M4 stretch target and remains an M5 deliverable if unfinished. VRF subscription setup, at least ten clean resolver addresses, exact ABI types, and Matthew's collateral proof are implementation gates; PR #28 approval is not evidence that M4 behavior already exists.
