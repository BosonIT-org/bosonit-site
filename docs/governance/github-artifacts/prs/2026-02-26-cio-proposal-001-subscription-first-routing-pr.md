## Summary
Implements governance artifacts for CIO Proposal 001 (subscription-first routing with controlled fallback).

## Linked Artifacts
- Issue: `docs/governance/github-artifacts/issues/2026-02-26-cio-proposal-001-subscription-first-routing.md`
- Design Note: `docs/governance/design-notes/DN-2026-02-26-cio-proposal-001-subscription-first-routing.md`
- Evidence: `docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/EVIDENCE.md`
- Decision Log: `docs/decisions/ADR-2026-02-26-cio-proposal-001-subscription-first-routing.md`

## Scope Classification
- [x] Governance/policy artifact changes
- [ ] Deploy-impacting implementation
- [ ] Infra-impacting implementation
- [ ] Security-impacting implementation

## Approval Gate
- If this PR expands into deploy/infra/security-impacting implementation, it must add `human-approval-required` and stop until explicit approval is recorded.

## Required Evidence
- At least one example trace per fallback reason_code.
- Ordered selection proof for normal path.
- Rejected trace example for non-allowed fallback trigger.

## Validation Checklist
- [x] Deterministic provider order documented.
- [x] Allowed/denied fallback triggers documented.
- [x] Fail-closed behavior documented for unknown state.
- [x] Rollback via `git revert` documented for pushed/shared changes.
