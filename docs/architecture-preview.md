# AC_ON Architecture Preview

AC_ON is a testnet-only decentralized esports prediction market. Users connect Coinbase Wallet and trade YES/NO shares on binary esports match outcomes.

Core market logic is planned to run on-chain on Ethereum Sepolia for Milestone 3. Off-chain services support esports API access, oracle automation, indexing, PostgreSQL derived data, and FastAPI queries. The system is not fully trustless or fully permissionless.

## Main System Architecture

```mermaid
flowchart TB
  user["User Roles<br/>Trader / Market Creator / Resolver"]
  frontend["React Frontend<br/>React + Vite + TypeScript<br/>Tailwind + wagmi + viem"]
  wallet["Coinbase Wallet"]

  subgraph client["USER / CLIENT"]
    user
    frontend
    wallet
  end

  subgraph offchain["OFF-CHAIN SERVICES"]
    api["FastAPI Backend"]
    rest["REST API"]
    oracle["Oracle Service"]
    indexer["Indexer Service<br/>Stores last processed block checkpoint<br/>Replays missed events after restart<br/>Reconciles stale DB state"]
    oracleWallet["Authorized Oracle Wallet / Signer"]
    db["PostgreSQL<br/>Derived / Indexed State Only<br/>NON-AUTHORITATIVE"]
    esports["Approved Esports APIs"]

    api --- rest
    api --- oracle
    api --- indexer
  end

  subgraph onchain["ON-CHAIN / AUTHORITATIVE STATE"]
    base["Ethereum Sepolia<br/>AUTHORITATIVE SOURCE OF TRUTH"]

    subgraph contracts["Smart Contract System"]
      market["PredictionMarket.sol<br/>main market contract<br/>market lifecycle<br/>YES / NO share balances<br/>trading<br/>trading deadline enforcement<br/>oracle proposals<br/>challenge state<br/>settlement<br/>payout claims<br/>emits market events"]
      lmsr["LMSR.sol Library<br/>on-chain pricing math<br/>trade cost calculation<br/>liquidity parameter logic<br/>no users or permissions"]
      resolver["ResolverRegistry.sol<br/>approved resolver pool<br/>resolver eligibility<br/>resolver admission later<br/>selected resolver validation<br/>conflict checks"]
    end

    base --- market
    base --- lmsr
    base --- resolver
  end

  resolverWallets["Independent Resolver Wallets"]
  apiNote["API credentials remain server-side.<br/>Never exposed to frontend or blockchain."]
  chainWins["If PostgreSQL state disagrees with blockchain state:<br/>BLOCKCHAIN WINS."]
  disputeRule["Dispute finalization rule<br/>3-of-5 selected resolver votes must match"]

  user -->|"uses application"| frontend
  frontend -->|"wallet connect / request signature"| wallet
  wallet -->|"signed transaction"| market
  frontend -->|"contract reads"| market
  frontend -->|"API request for market data"| rest
  rest -->|"derived/indexed market data"| frontend

  rest <-->|"query derived/indexed data"| db
  market -->|"event logs"| indexer
  resolver -->|"event logs"| indexer
  indexer -->|"indexed / derived data"| db
  market -->|"contract events for reconciliation"| indexer
  market -.->|"uses pricing library"| lmsr
  market -.->|"checks resolver status"| resolver

  oracle -->|"HTTPS request + server-side API credentials"| esports
  esports -->|"match result"| oracle
  oracle -->|"uses authorized signer"| oracleWallet
  oracleWallet -->|"propose outcome<br/>authorized oracle only"| market
  oracle -.-> apiNote

  resolverWallets -->|"resolver vote transaction"| market
  market -->|"validates resolver eligibility/conflicts"| resolver
  market -.-> disputeRule
  chainWins -.-> db
  chainWins -.-> market

  style client fill:#eef6ff,stroke:#2563eb,stroke-width:1px
  style offchain fill:#f8fafc,stroke:#64748b,stroke-width:1px
  style onchain fill:#ecfdf5,stroke:#059669,stroke-width:1px
  style db fill:#fff7ed,stroke:#ea580c,stroke-width:2px
  style base fill:#dcfce7,stroke:#15803d,stroke-width:2px
  style chainWins fill:#fee2e2,stroke:#dc2626,stroke-width:2px
  style disputeRule fill:#fef9c3,stroke:#ca8a04,stroke-width:2px
```

### Authorization Notes

- The oracle may propose outcomes through an authorized oracle wallet.
- The oracle may not directly settle disputed markets, bypass the challenge period, or vote as a human resolver.
- Resolver wallets are independent from the automated oracle.
- Resolver voting authorization is enforced by contracts:
  - active resolver
  - selected for the dispute
  - no prohibited conflict
- The market creator, result proposer, and challenger must not resolve their own disputed market.

### On-Chain Contract Split

- `PredictionMarket.sol` is the main user-facing contract for market state, trading, disputes, settlement, and claims.
- `LMSR.sol` is a Solidity library used by `PredictionMarket.sol` for on-chain pricing math. It is not an off-chain service and users do not call it directly.
- `ResolverRegistry.sol` stores the approved resolver pool and resolver eligibility rules. `PredictionMarket.sol` checks it when resolver votes are submitted.

### Database Authority And Recovery

- PostgreSQL stores derived/indexed data only.
- PostgreSQL may contain market lists, price history, trade history, resolver history, and derived market metadata.
- PostgreSQL must not be presented as the source of truth.
- The indexer should resume from the last processed block, replay missed events, and repair stale derived state.
- PostgreSQL does not write authoritative state into smart contracts.

## Market State Machine

```mermaid
stateDiagram-v2
  [*] --> CREATED
  CREATED --> OPEN: market activated
  OPEN --> CLOSED: trading deadline reached
  CLOSED --> PROPOSED: oracle proposes result
  CLOSED --> ORACLE_TIMEOUT: oracle cannot retrieve usable result
  CLOSED --> VOID: canceled / no-contest match

  PROPOSED --> FINALIZED: challenge window expires
  PROPOSED --> DISPUTED: valid challenge
  DISPUTED --> RESOLVER_VOTING: 5 eligible resolvers selected
  ORACLE_TIMEOUT --> RESOLVER_VOTING: timeout escalated for human resolution
  RESOLVER_VOTING --> FINALIZED: 3-of-5 matching votes
  FINALIZED --> CLAIMABLE: winning positions redeemable
```

### Exceptional States

```mermaid
flowchart TB
  postponed["POSTPONED<br/>settlement waits for rescheduled result"]
  timeout["ORACLE_TIMEOUT<br/>oracle cannot retrieve usable result<br/>does not auto-finalize or auto-void"]
  resolverPath["Resolver Voting<br/>manual/human resolution path"]
  voided["VOID<br/>canceled / no-contest match<br/>no YES/NO winner"]
  refundRule["Void settlement rule<br/>each outstanding YES or NO share redeems for 0.5 testnet tokens"]

  postponed --> timeout
  timeout --> resolverPath
  voided --> refundRule
```

`ORACLE_TIMEOUT` means the system does not have a reliable result yet. It should not silently choose a winner and should not automatically become `VOID`. A timed-out market remains unresolved until it is escalated to resolver voting or another explicitly defined manual resolution path.

## Trust Model

- Core trading and settlement rules are enforced on-chain.
- External esports APIs remain trusted off-chain dependencies.
- Initial approved APIs are configured by the project team.
- The automated oracle proposes outcomes but cannot unilaterally settle challenged markets.
- The initial resolver pool is bootstrapped manually.
- Disputes are decided by multiple resolvers, not one centralized operator.
- Five eligible resolvers are selected for a dispute.
- Three matching votes are required.
- Oracle and human resolver are separate actors.

## Authority Table

| Data / Action | Authoritative Source |
| --- | --- |
| Market state | Ethereum Sepolia smart contracts |
| YES/NO ownership | Ethereum Sepolia smart contracts |
| LMSR pricing/trades | Ethereum Sepolia smart contracts |
| Resolver votes | Ethereum Sepolia smart contracts |
| Settlement | Ethereum Sepolia smart contracts |
| Payout status | Ethereum Sepolia smart contracts |
| Esports match result input | Approved external APIs via oracle |
| Market list cache | PostgreSQL |
| Price/trade history cache | PostgreSQL |
| UI display state | Derived from chain/backend |

## Architecture Feedback Coverage

- [x] On-chain and off-chain boundaries
- [x] Blockchain state is authoritative
- [x] PostgreSQL is derived/indexed only
- [x] Oracle wallet authorization
- [x] Resolver authorization
- [x] API credential boundary
- [x] Stale indexer recovery
- [x] Database vs blockchain disagreement behavior
- [x] Oracle and resolver are separate actors
- [x] Market state-machine diagram
