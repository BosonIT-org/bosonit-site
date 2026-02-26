## Title
CIO Proposal 001 Implementation Workpack: subscription-first routing policy execution

## Objective
Convert Proposal 001 into controlled implementation tasks with deterministic gates, evidence capture, and rollback readiness.

## Linked Source Artifacts
- Parent Issue: `docs/governance/github-artifacts/issues/2026-02-26-cio-proposal-001-subscription-first-routing.md`
- Parent Design Note: `docs/governance/design-notes/DN-2026-02-26-cio-proposal-001-subscription-first-routing.md`

## Workpack Tasks
- Define policy contract fields: `provider_order`, `fallback_triggers_allowed`, `fallback_triggers_denied`, `fail_closed_default`.
- Implement selector logic in scoped policy files only.
- Add routing decision telemetry fields required by evidence template.
- Add deterministic tests for each trigger path and blocked path.
- Attach evidence for each test class and required CI checks.

## Hard Gates
- Any deploy/infra/security-impacting expansion is blocked pending explicit human approval.
- Required checks must pass: `security / gitleaks`, `policy / habitat-guardrails`, `ci / test`.
- Unknown policy state defaults to blocked.

## Acceptance Criteria
- Implementation PR artifact is complete.
- Evidence template is populated with real traces.
- ADR is updated to `Accepted` after approval and checks pass.

## Links
- Implementation Design Note: `docs/governance/design-notes/DN-2026-02-26-cio-proposal-001-routing-implementation-plan.md`
- Implementation PR Artifact: `docs/governance/github-artifacts/prs/2026-02-26-cio-proposal-001-routing-implementation-pr.md`
- Implementation Evidence Template: `docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/IMPLEMENTATION-EVIDENCE-TEMPLATE.md`
- Implementation ADR: `docs/decisions/ADR-2026-02-26-cio-proposal-001-routing-implementation.md`
