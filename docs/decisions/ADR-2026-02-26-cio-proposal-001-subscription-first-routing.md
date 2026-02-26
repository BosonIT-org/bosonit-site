# ADR: CIO Proposal 001 - Subscription-First Routing with Controlled Fallback

## Status
Proposed

## Date
2026-02-26

## Context
BosonIT needs stable model quality and rate-limit resilience without drift into unmanaged fallbacks.

## Decision
Define and enforce subscription-first routing order with explicit fallback triggers and fail-closed behavior for unknown states.

## Guardrails
- Human approval is required before any deploy/infra/security-impacting implementation.
- Silent downgrade paths are not permitted.
- Evidence is mandatory for routing decisions and fallback reasons.

## Consequences
- Better quality consistency.
- Better cost control and observability.
- Additional policy overhead offset by deterministic operations.

## Rollback
Use `git revert` for pushed/shared history.

## References
- Onboarding policy: `/Users/kennethjones/Documents/Onboarding-ChatGPT-Codex.json`
- Issue: `docs/governance/github-artifacts/issues/2026-02-26-cio-proposal-001-subscription-first-routing.md`
- Design Note: `docs/governance/design-notes/DN-2026-02-26-cio-proposal-001-subscription-first-routing.md`
- PR Artifact: `docs/governance/github-artifacts/prs/2026-02-26-cio-proposal-001-subscription-first-routing-pr.md`
- Evidence: `docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/EVIDENCE.md`
