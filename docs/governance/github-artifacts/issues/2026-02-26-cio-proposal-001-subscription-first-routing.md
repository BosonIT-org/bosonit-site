## Title
CIO Proposal 001: Subscription-first model routing with fail-closed fallback policy

## Problem
Model routing can drift into lower-quality fallback paths, increase latency, and weaken predictable governance if provider order and fallback triggers are not explicit.

## Objective
Implement deterministic routing policy:
- Primary order: Codex -> Gemini -> Claude
- Fallback only on hard triggers: rate-limit, outage, quota exhaustion
- Last resort: Cerebras/local mesh

## Scope
- Policy and control-plane logic only.
- No direct deploy action in this issue.

## Business Value
- Improve response quality consistency.
- Reduce avoidable token waste from overlap and repeated retries.
- Increase auditability of routing decisions.

## Risk and Controls
- Any deploy/infra/security-impacting implementation step requires explicit human approval.
- Unclear classification defaults to blocked (fail-closed).

## Acceptance Criteria
- Design note defines trigger matrix and precedence.
- PR artifact includes deterministic checklists and required evidence.
- Evidence captures sample decision traces and fallback reasons.
- ADR records decision and rollback posture.

## Links
- Design Note: `docs/governance/design-notes/DN-2026-02-26-cio-proposal-001-subscription-first-routing.md`
- PR Artifact: `docs/governance/github-artifacts/prs/2026-02-26-cio-proposal-001-subscription-first-routing-pr.md`
- Evidence: `docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/EVIDENCE.md`
- Decision Log: `docs/decisions/ADR-2026-02-26-cio-proposal-001-subscription-first-routing.md`
