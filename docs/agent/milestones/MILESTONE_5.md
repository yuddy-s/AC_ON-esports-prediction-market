# Milestone 5: Testing and Integration

Status: planned

## Course Goal

Present integration test results, defects and fixes, and the deployment plan. The proposed M4 plan moves the first public Ethereum Sepolia feature-complete deployment into M4; M5 repeats and hardens that deployment, reports remaining defects and fixes, and delivers draft user/developer guides. If M4 public acceptance does not pass, carry its unmet path forward explicitly rather than claiming it was completed.

## Testing And Deployment Ownership

- Adriel repeats frontend journeys and wallet/browser behavior on the M4 Vercel deployment, fixes discovered defects, and drafts the user guide.
- Benny runs expanded contract security/static checks, deployment verification, and settlement/claim regression tests on Ethereum Sepolia.
- Matthew analyzes failed economic properties and publishes LMSR/accounting test results and parameter rationale.
- Yudhveer repeats API/indexer/oracle integration, retry/replay/reorganization and database-rebuild tests against the M4 Render/Supabase deployment, strengthens monitoring/recovery, and drafts the developer guide.
- The team triages integration defects, records fixes and residual risks, and runs the complete public deployment acceptance checklist.

## Exit Criteria

- Public Vercel, Render, Supabase, and Ethereum Sepolia components continue to work together after regression, failure-recovery, and security testing; any M4 deployment gap is closed and evidenced.
- Integration results include transaction submission, mining, indexing, API reflection, oracle proposal, dispute, resolver voting, finalization, and claim paths.
- Secrets are hosted outside source control and rotation/revocation steps are documented.
- Draft user and developer guides reproduce setup, deployment, recovery, and normal product use.
- NGINX is not part of the managed Render deployment; reconsider it only for future self-hosting.
