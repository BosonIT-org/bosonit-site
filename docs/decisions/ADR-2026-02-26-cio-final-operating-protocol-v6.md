# ADR: CIO Final Operating Protocol v6.0.0

## Status
Accepted

## Date
2026-02-26

## Context
BosonIT finalized the CIO operating protocol for post-onboarding governance and control-plane execution through GitHub.

## Decision
Adopt `/Users/kennethjones/bosonit.org/docs/governance/CIO_FINAL_OPERATING_PROMPT_v6.json` as the active protocol source for CIO operations.

## Key Rules Adopted
- Fail-closed governance is mandatory.
- Required checks are exact-name enforced:
  - `security / gitleaks`
  - `policy / habitat-guardrails`
  - `ci / test`
  - `habitat-warden`
  - `ai-ops auto-approve`
- Sensitive-path gate uses delegated single-human mode:
  - required label: `human-approval-required`
  - required team review request: `ai-ops`
- No secrets, no pushed-history rewrite, scoped reversible changes only.

## Platform Constraint
GitHub Actions cannot submit approval reviews (`422` restriction). Delegated gate compliance is therefore represented by:
- gate label present, and
- `ai-ops` team review request present, and
- required checks passing.

## Consequences
- Governance execution remains automatable with one human owner.
- Approval semantics are explicit and auditable.
- Habitat enforcement remains fail-closed for sensitive paths.

## Rollback
For pushed/shared corrections, use `git revert <sha>` and record incident evidence.
