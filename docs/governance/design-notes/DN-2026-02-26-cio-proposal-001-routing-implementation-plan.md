# Design Note: CIO Proposal 001 Implementation Plan

## Goal
Implement subscription-first routing with explicit fallback triggers and fail-closed behavior in a controlled, testable sequence.

## In Scope
- Policy schema and selector behavior.
- Fallback trigger evaluation logic.
- Routing telemetry fields for audit evidence.
- Deterministic tests for normal, fallback, and blocked paths.

## Out of Scope
- Unrelated feature expansion.
- New provider integrations beyond existing approved providers.
- Direct production deploy actions without explicit human approval.

## Policy Contract
- `provider_order`: `openai-codex`, `gemini-pro`, `claude-opus`, `claude-sonnet`
- `fallback_allowed`: `rate_limit`, `provider_outage`, `quota_exhausted`
- `fallback_denied`: `manual_preference`, `silent_downgrade`, `unknown_reason`
- `default_on_unknown`: `block`

## Implementation Sequence
1. Add policy contract and validation checks.
2. Implement ordered selector behavior.
3. Implement fallback reason-code gate.
4. Add telemetry fields to every decision.
5. Add deterministic test coverage and evidence capture.

## Required Evidence
- One trace for normal primary route.
- One trace per allowed fallback trigger.
- One blocked trace for denied trigger.
- CI check pass evidence for required checks.

## Rollback
- Unpushed fix: local correction allowed.
- Pushed/shared fix: `git revert <sha>`.
- Policy or secret violation: immediate stop, revert, incident record, evidence attachment.
