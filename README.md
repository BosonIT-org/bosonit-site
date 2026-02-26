# BosonIT Site

Customer-facing applications, delivery workflows, and runtime service code for BosonIT.

## Three-repo habitat map
- `BosonIT-org/bosonit-site`: product and delivery surface (this repo)
- `BosonIT-org/bosonit-habitat-core`: governance, policy, control-plane automation
- `BosonIT-org/bosonit-habitat-observatory`: evidence, telemetry, records management

## In scope
- Web and application code for BosonIT services
- Deployment entrypoints and environment-safe release changes
- Product-facing configuration required for runtime behavior

## Out of scope
- Global governance contracts and policy schemas (use habitat-core)
- Enterprise evidence archives and observatory records (use habitat-observatory)

## Standard operating workflow
1. Create a branch.
2. Open a PR with hypothesis, KPI, risk class, rollback, owner, and links.
3. Pass required checks before merge.
4. Use squash merge unless an ADR explicitly approves another method.

## Governance requirements
- Sensitive-path PRs require `human-approval-required` and `ai-ops` team review.
- Fail-closed behavior applies for infra, security, and deploy-impacting changes.
- No secrets in git; use Vault-managed references only.
