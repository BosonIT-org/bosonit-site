# Design Note: CIO Onboarding to Habitat Control Plane

## Context
BosonIT is integrating ChatGPT 5.2 Pro as Senior Chief Innovations Officer (CIO). Innovation proposals must accelerate execution without weakening Habitat controls.

## Decision
Adopt a GitHub-first operating flow:
Issue -> Design Note -> PR -> Evidence -> Decision Log.

## Boundary Law
- CIO may propose and author changes.
- Any deploy/infra/security-impacting change is blocked until explicit human approval is recorded.
- Unknown classification defaults to blocked (fail-closed).

## Control Mapping
- Policy source: `/Users/kennethjones/Documents/Onboarding-ChatGPT-Codex.json`
- Branch rule: `codex/` prefix for implementation branches.
- Required checks: `security / gitleaks`, `policy / habitat-guardrails`, `ci / test`.
- Rollback rule: use `git revert` for pushed/shared history.

## Data Classification and Risk
- `public/internal`: advisory and documentation updates allowed within scope.
- `confidential/restricted`: require redaction controls and explicit approval workflow.

## Outputs
- Issue artifact for kickoff.
- PR artifact template with compliance checklist.
- Evidence baseline record for traceability.
- ADR documenting adoption and constraints.

## Success Signal
Every innovation change set is traceable and reviewable with objective evidence, deterministic gates, and explicit approvals when required.
