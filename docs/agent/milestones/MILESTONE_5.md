# Milestone 5: Testing and Integration

Status: planned

## Course Goal

Present integration test results, defects and fixes, and the deployment plan. The course places the public Ethereum Sepolia deployment in M5. The proposed M4 plan targets an earlier public application as an additional team goal, pending explicit team agreement; M5 repeats and hardens it if achieved, or completes it if still pending. M5 also delivers draft user/developer guides.

## Testing And Deployment Ownership

- Adriel validates frontend journeys and wallet/browser behavior on Vercel, deploys it if M4 did not, fixes discovered defects, and drafts the user guide.
- Benny runs expanded contract security/static checks, deployment verification, and settlement/claim regression tests on Ethereum Sepolia.
- Matthew analyzes failed economic properties and publishes LMSR/accounting test results and parameter rationale.
- Yudhveer validates API/indexer/oracle integration, retry/replay/reorganization and database-rebuild tests on Render/Supabase, deploys those services if M4 did not, strengthens monitoring/recovery, and drafts the developer guide.
- The team triages integration defects, records fixes and residual risks, and runs the complete public deployment acceptance checklist.

## Exit Criteria

- Public Vercel, Render, Supabase, and Ethereum Sepolia components work together after regression, failure-recovery, and security testing; any M4 deployment gap is closed and evidenced.
- Integration results include transaction submission, mining, indexing, API reflection, oracle proposal, dispute, resolver voting, finalization, and claim paths.
- Secrets are hosted outside source control and rotation/revocation steps are documented.
- Draft user and developer guides reproduce setup, deployment, recovery, and normal product use.
- NGINX is not part of the managed Render deployment; reconsider it only for future self-hosting.
