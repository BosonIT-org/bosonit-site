# ADR: Onboard ChatGPT 5.2 Pro CIO to Fail-Closed Habitat Control Plane

## Status
Accepted

## Date
2026-02-26

## Context
BosonIT needs innovation throughput without weakening governance for deploy, infra, and security boundaries.

## Decision
Adopt and enforce a GitHub artifact chain for CIO operations:
Issue -> Design Note -> PR -> Evidence -> Decision Log.

## Constraints
- CIO can propose and author changes.
- Deploy/infra/security-impacting changes require explicit human approval before merge or execution.
- Policy uncertainty defaults to blocked.

## Consequences
- Higher traceability and audit quality.
- Slightly more process overhead offset by clearer approvals and rollback decisions.

## Rollback Standard
If a bad pushed/shared change occurs, `git revert` is the required rollback mechanism.

## References
- `/Users/kennethjones/Documents/Onboarding-ChatGPT-Codex.json`
- `docs/governance/github-artifacts/issues/2026-02-26-cio-onboarding-kickoff.md`
- `docs/governance/design-notes/DN-2026-02-26-cio-onboarding-control-plane.md`
- `docs/governance/github-artifacts/prs/2026-02-26-cio-onboarding-kickoff-pr.md`
- `docs/governance/evidence/2026-02-26/cio-onboarding-kickoff/EVIDENCE.md`
