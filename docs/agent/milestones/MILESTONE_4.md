# Milestone 4: Feature-Complete

Status: planned

## Course Goal

Demonstrate the complete planned feature set, explain trade-offs made while finishing it, present the testing and integration plan, and deliver the complete implementation plus final-design documentation.

## Feature-Complete Target

- Adriel completes market creation/browsing, buy/sell, positions, challenges, resolver voting, settlement/claim, VOID, and error/recovery UI flows.
- After team approval, Benny completes the authoritative market lifecycle, access control, challenge, settlement, claim, and `VOID` contracts, including the proposed multisignature-administered resolver registry, snapshotted candidate pools, current-request-only Chainlink VRF committee selection, conflict checks, two-round voting fallback, and direct-vote authorization.
- Matthew completes LMSR sell behavior, subsidy and bounded-loss accounting, payout/VOID accounting, and the economic invariant suite. Trading/platform fees remain out of scope.
- Yudhveer completes production esports-provider adapters, least-privilege oracle signing, all event projections/APIs, resolver status/history, and replay/reorganization support.
- The team freezes the final ABI, state terminology, event schema, secrets model, and full documented test plan.

## Exit Criteria

- Every planned user feature works across frontend, contracts, backend, and database.
- Resolver selection and votes are enforced on-chain; PostgreSQL remains derived.
- Resolver tests cover registry changes, address-level conflict exclusions, candidate snapshots, fixed selection deadlines across VRF retries, stale/duplicate/late callback rejection, five-resolver selection, one vote per resolver, three-of-five quorum, replacement committee selection, both 48-hour voting deadlines, seven-day formation fallbacks, and terminal `VOID` behavior.
- Oracle data fetching and signing are separated, retryable, and auditable.
- All component suites pass and the cross-layer integration suite covers normal and disputed market paths.
- Architecture, sequence/state diagrams, API documentation, and setup instructions match the final implementation.
