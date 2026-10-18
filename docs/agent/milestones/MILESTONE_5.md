# Milestone 5: Testing and Integration

Status: planned

## Course Goal

Present integration test results, defects and fixes, and the deployment plan. Deliver test results, a public Ethereum Sepolia deployment, and draft user/developer guides.

## Testing And Deployment Ownership

- Adriel validates frontend journeys and wallet/browser behavior, deploys the frontend to Vercel, and drafts the user guide.
- Benny runs contract security/static checks, deployment verification, and settlement/claim regression tests on Ethereum Sepolia.
- Matthew analyzes failed economic properties and publishes LMSR/accounting test results and parameter rationale.
- Yudhveer runs API/indexer/oracle integration, retry/replay/reorganization and database-rebuild tests; deploys FastAPI/background services to Render and PostgreSQL to Supabase; drafts the developer guide.
- The team triages integration defects, records fixes and residual risks, and runs the complete public deployment acceptance checklist.

## Exit Criteria

- Public Vercel, Render, Supabase, and Ethereum Sepolia components work together.
- Integration results include transaction submission, mining, indexing, API reflection, oracle proposal, dispute, resolver voting, finalization, and claim paths.
- Secrets are hosted outside source control and rotation/revocation steps are documented.
- Draft user and developer guides reproduce setup, deployment, recovery, and normal product use.
- NGINX is not part of the managed Render deployment; reconsider it only for future self-hosting.
