# Shared Test Vectors

## `market_deadline_vectors.json` (issue #53)

One set of market state and timestamp cases for the contract, the indexer/API and the frontend.

**Stored state vs effective phase.** The contract is the only authority for market state.
`getMarket().state` (and the indexer's projection of lifecycle events) is the *stored* state. It
stays `OPEN` after the trading deadline until a state-changing transaction (`closeTrading`,
`proposeOutcome` or `requestResolverSelection`) closes it. The contract still rejects trades at and
after the deadline (`TradingClosed`). The frontend therefore derives an *effective* phase from the
stored state plus chain time and shows "Trading closed" for an expired `OPEN` market. The backend
reports the raw stored state and deadline. It must not invent a second lifecycle authority.

Each vector gives `storedState`, `tradingDeadline` and `blockTimestamp`, and the expected contract
result:

| Field | Meaning |
|---|---|
| `tradeAccepted` | `buy`/`sell` succeeds (state `OPEN` and `blockTimestamp < tradingDeadline`) |
| `proposalAccepted` | `proposeOutcome` passes its time checks (`tradingDeadline <= t < tradingDeadline + 7 days`) |
| `noProposalSelectionAccepted` | `requestResolverSelection` succeeds without a dispute (`t >= tradingDeadline + 7 days`) |
| `frontendActions` | Actions the frontend phase offers with no proposal recorded (omitted for terminal states) |

## Consumers

| Layer | Test | Status |
|---|---|---|
| Frontend | `frontend/src/deadlineVectors.test.ts` (tradability and effective phase per vector) and `frontend/src/TradePanel.test.tsx` (an expired `OPEN` market renders "Trading is closed for this market." with the buy button disabled; a positive control before the deadline is enabled) | in place |
| Contracts | Foundry test that warps to each `blockTimestamp` and asserts `tradeAccepted`, `proposalAccepted` and `noProposalSelectionAccepted` (Foundry can read this file with `vm.readFile` once `fs_permissions` allows it) | owner: Benny |
| Backend/API | Pytest that indexes the matching lifecycle events and asserts the API returns the raw `storedState` and `tradingDeadline` | owner: Benny / Yudhveer |

Change a vector only together with the contract rule it describes, and update every consumer in
the same PR.
