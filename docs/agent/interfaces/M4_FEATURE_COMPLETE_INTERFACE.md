# Proposed Milestone 4 Feature-Complete Interface

Status: **proposed for team discussion, not approved or implemented**. This record extends the [approved M3 trading interface](M3_TRADING_INTERFACE.md) for a new M4 deployment. No Solidity, frontend, oracle, or indexer agent should treat a candidate name or rule below as a frozen ABI until team approval is recorded in the discussion PR and the exact interface is updated here.

## Why A New Interface Is Needed

The deployed M3 contract supports ACON-funded creation and guarded buys, but has no sell, explicit close, oracle, challenge, resolver, settlement, VOID payout, or claim functions. Its single-market frontend and market/trade-only indexer cannot present the full lifecycle. A new Sepolia deployment, exact-build ABI, deployment block, and versioned manifest are required; the M3 deployment remains historical and must not be silently treated as M4 state.

## Proposed User And Fixture Flow

1. A server-side PandaScore adapter imports upcoming and past match fixtures/results for Valorant, Counter-Strike 2, and Rainbow Six Siege. The deterministic mock adapter has the same normalized contract for tests. Verify the free-tier fields, account access, and permitted prediction-market use before relying on the live feed. [PandaScore plan reference](https://developers.pandascore.co/docs/plan-reference) lists basic fixture/results access; CS2 endpoints retain the `/csgo/` prefix.
2. A restricted fixture registrar reviews an imported match and records a canonical fixture key, provider/game/match identity, two team identities, and scheduled start on-chain. Candidate key: `keccak256(abi.encode(provider, game, externalMatchId))`; the exact encoding and metadata/event shape must be frozen together. Importing a fixture into PostgreSQL does **not** register it or create a market.
3. Any funded user may create a market from an on-chain registered fixture and supply the required ACON subsidy. The contract rejects unknown fixture keys and enforces a trading deadline no later than the registered start. YES means the registered first team wins; NO means the registered second team wins. A canceled, postponed, tied, or otherwise unsupported result must use an explicit pending/VOID rule, never be mapped to a false binary winner. Multiple markets may refer to the same fixture unless the team changes this proposed rule.

This registry prevents direct calls from using an **unregistered** match ID. It does not cryptographically verify PandaScore; the registrar and provider remain explicit trust dependencies. Automatic registration of every imported fixture is not proposed because it would spend gas on unused listings. The frontend may show more imported fixtures than are currently registered but must label when creation is unavailable.

## Candidate Contract Boundaries For Review

| Boundary | Proposed behavior | Approval needed |
|---|---|---|
| Roles | Separate fixture registrar, outcome proposer, and resolver-registry administrator; user transactions remain wallet-signed. Multisignature administration is proposed for the resolver allowlist. | Role assignment, revocation, rotation, and whether the fixture registrar may be automated. |
| Trading | Keep M3 `quoteBuy`/guarded `buy`; add `quoteSell` and `sell(..., minReturn)` that burns only owned shares and pays the current LMSR cost decrease. Stop both sides at the deadline and after lifecycle progression. | Exact function/event signatures, 1e18 rounding, and reentrancy/accounting proof. |
| Proposal/challenge | An authorized proposer can submit YES/NO with evidence reference after trading closes. A proposal has a proposed **24-hour challenge window**. A valid challenge moves to the resolver path; an unchallenged proposal may finalize only after the window. | Challenge eligibility, bond/cost rule, evidence encoding, correction and timeout behavior. |
| Resolver | From the proposed on-chain allowlist, snapshot non-conflicted candidates; Chainlink **VRF v2.5** selects five distinct addresses. Only the current request for the market/round may install a committee before its fixed seven-day selection deadline. Each resolver votes YES/NO/VOID once in a 48-hour round: three matching YES/NO votes finalize that winner, while three matching VOID votes make the market VOID. One replacement round follows a first-round failure; the documented deadline/quorum fallbacks lead to VOID. | Explicit approval of administrator/VRF dependency, request/funding configuration, conflict and liveness rules. [Chainlink VRF docs](https://docs.chain.link/vrf) |
| Claims | Proposed winner payout is 1 ACON per outstanding winning share; proposed VOID payout is 0.5 ACON per outstanding YES or NO share. A claim can execute once per wallet/outcome and must preserve sufficient reserves. | Matthew's solvency/rounding proof, claim and creator-surplus rules, and exact event/read interface. |

The conflict proposal excludes the market creator, oracle proposer, challenger, and any address recorded on-chain as trading in or holding a position in that market. Checks are address-level; related undisclosed wallets cannot be detected. Candidate snapshots, retry deadlines, stale callbacks, and replacement-round rules remain as proposed in [the M3 resolver discussion](../milestones/MILESTONE_3.md#resolver-boundary), pending explicit M4 approval.

## Candidate Events, Reads, And Consumer Handoff

The ABI freeze must define complete, indexed event identities and payloads for fixture registration, market creation, buy, sell, close, outcome proposal, challenge, selection request/fulfillment/ignored callback, resolver vote, finalization, VOID, payout claim, and creator-surplus withdrawal. Preserve the M3 buy-event meaning; a separate sell event is the proposed way to avoid treating a payout as a positive buy cost. Include sufficient post-event market state for deterministic indexer replay and API reconciliation. Publish the compiled ABI and manifest with source commit, chain ID, token/market addresses, deployment block, ABI digest, roles, and example transactions; never guess them in source or docs.

The frontend submits user writes through the wallet and reads spendable positions, resolver eligibility, and claimability from the contract. The backend does not submit user trades, challenges, votes, or claims. The indexer consumes confirmed contract events with its existing unique-log/checkpoint/reorg model and publishes derived fixture, market, trade, resolution, and claim history through FastAPI. API rows identify the indexed chain/contract, safe checkpoint, and freshness; PostgreSQL never selects resolvers, counts authoritative votes, or settles a market.

## Decisions To Resolve In The Discussion PR

- Confirm PandaScore account fields/coverage and usage terms for this test-token prediction product; approve result finality and evidence/correction rules for each game.
- Approve the on-chain fixture key, team mapping, registration authority, scheduled-start/deadline rule, early-start/postponement/cancellation handling, and whether multiple markets per fixture are allowed. In particular, decide how trading closes if a match begins before its registered start without letting an administrator silently rewrite positions.
- Approve sell rounding and `minReturn`, challenge eligibility/bond or anti-spam rule, oracle timeout/cancellation transitions, and all state/event/function shapes.
- Accept or revise the proposed resolver administrator, VRF v2.5 payment/request configuration, five-resolver/two-round rules, fixed deadlines, and address-level conflict limitations.
- Accept or revise winning/VOID payout math and creator-surplus withdrawal after Matthew proves liabilities under buys, sells, and rounding.
- Name owners of registrar/proposer/VRF funds, multisignature wallet, five eligible resolver wallets, hosted secrets, and rotation/revocation procedures.

Record decisions and approvals in the PR discussion, then replace candidate language with the approved ABI/event table before dependent implementation PRs merge. A merged planning PR alone does not prove any M4 path works.
