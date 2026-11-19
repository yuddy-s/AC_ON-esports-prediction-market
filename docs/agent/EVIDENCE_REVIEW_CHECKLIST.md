# Independent Fixture And Result Evidence Review

Status: required M5 operator procedure. Written permission for the educational PandaScore use was
privately confirmed by the team on November 18, 2026. The permission record and provider token are
not repository artifacts. PandaScore remains informational and cannot independently authorize a
registration or proposal.

## Independence Gate

Before approving anything, establish that the evidence URL is controlled by the tournament
organizer, league, or another source independent of the imported provider. Record how domain
ownership was established. `pandascore.co` and every subdomain are always ineligible. Social posts,
search-result pages, unsourced screenshots, and copied provider pages are insufficient.

Store only the public evidence URL and its SHA-256 content/reference hash. Never store access tokens,
session cookies, private correspondence, or credentials in the audit record.

## Fixture Approval

Check every item against the exact imported fixture observation:

- Provider, game, external match ID, competition, and organizer identify one match.
- Game title is supported and unambiguous.
- Team A identity and name are correct; Team A maps permanently to YES.
- Team B identity and name are correct; Team B maps permanently to NO.
- Scheduled start, timezone, match format, and current status agree.
- Provider source timestamp is not older than the independent evidence.
- Independent URL opens successfully and its hash is recorded.
- No duplicate fixture or already-registered fixture key exists.

Reject or defer if the teams, order, schedule, identity, or status disagree. A postponement or team
replacement changes registration-sensitive data and requires a new observation and review. An
imported or reviewed fixture remains off-chain until the registrar confirms the receipt and matching
contract read.

## Result Approval

Review the exact append-only result observation, not merely the current fixture:

- Match identity, game, teams, and Team A/YES ordering match the registered fixture.
- Status is final according to the independent organizer evidence.
- Winner identity is explicit and agrees with the imported observation.
- Source timestamp, independent URL, and evidence hash are recorded.
- The observation is the newest known result; earlier observations remain unchanged.

Map a final Team A win to YES and Team B win to NO. Map an organizer-confirmed tie, cancellation,
no-contest, or unsupported final result to VOID. Treat an ambiguous winner, ongoing/postponed match,
conflicting source, or missing evidence as not reviewable; do not create a proposal intent.

For forfeits, use the organizer's officially declared winner only when the competition treats the
forfeit as final. Otherwise defer or use VOID when the final organizer status supports it. A
correction must be imported as a new observation, receive its own independent review, and enter the
correction/challenge workflow; never edit an earlier observation or proposal.

## Audit And Failure Rules

- Record reviewer identity, decision time, exact observation/fixture ID, evidence URL/hash, and the
  identity hash used by the registration or proposal state machine.
- A rejection or revocation is append-only. Never delete the earlier decision.
- During provider 429, outage, access denial, malformed response, or conflicting pagination, retain
  the last timestamped observation and stop new automated proposal work.
- Manual JSON and deterministic mock adapters remain recovery/test paths. Label them non-authoritative
  and apply the same review before any Sepolia registrar or proposer submission.
- Rebuild only chain-derived projections. Provider observations, reviews, assessments, signer jobs,
  intents, attempts, and audit records must survive.

## Operator Commands

Run from `backend/` after independently calculating the evidence hash:

```text
python -m scripts.review_fixture FIXTURE_ID --reviewer OPERATOR_ID --approve --evidence-url ORGANIZER_URL --evidence-hash 0xSHA256
python -m scripts.review_result OBSERVATION_ID --reviewer OPERATOR_ID --approve --evidence-url ORGANIZER_URL --evidence-hash 0xSHA256
```

Use `--revoke` for a later rejection. Inspect the append-only review row before activating a
registrar job or allowing the proposer to process an intent.
