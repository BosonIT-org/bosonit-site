# ADR: Proposal 001 Routing Implementation

## Status
Accepted

## Date
2026-02-26

## Context
Proposal 001 requires operational implementation details that preserve fail-closed governance and explicit human approval boundaries.

## Decision
Adopt the implementation plan and PR evidence process defined in:
- `docs/governance/design-notes/DN-2026-02-26-cio-proposal-001-routing-implementation-plan.md`
- `docs/governance/github-artifacts/prs/2026-02-26-cio-proposal-001-routing-implementation-pr.md`
- `docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/IMPLEMENTATION-EVIDENCE-TEMPLATE.md`

## Approval Requirement
Any deploy/infra/security-impacting scope change requires explicit human approval before merge or execution.

## Approval Record
- Approved by: `BosonIT owner (in-thread authorization)`
- Approval date: `2026-02-26`
- Approval scope: `complete full onboarding process for CIO Proposal 001`

## Enforcement
- Unknown routing reason defaults to blocked.
- Required checks must pass: `security / gitleaks`, `policy / habitat-guardrails`, `ci / test`.

## Rollback
If pushed/shared and incorrect behavior is introduced, execute `git revert <sha>` and attach incident evidence.
