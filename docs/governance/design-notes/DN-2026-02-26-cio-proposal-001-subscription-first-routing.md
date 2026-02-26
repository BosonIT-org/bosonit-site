# Design Note: CIO Proposal 001 - Subscription-First Routing

## Context
BosonIT runs multiple model providers across local and remote agents. Routing needs deterministic quality-first order, cost-awareness, and fail-closed governance.

## Decision
Adopt a strict routing policy:
1. `openai-codex` (primary)
2. `gemini-pro` (secondary)
3. `claude-opus/sonnet` (tertiary)
4. `cerebras-proxy` and `local-mesh` only on fallback triggers.

## Fallback Triggers (Allowed)
- Provider rate-limit reached.
- Provider service outage or timeout threshold breached.
- Quota exhaustion confirmed.

## Fallback Triggers (Not Allowed)
- Preference-only switching.
- Undocumented manual override.
- Silent downgrade without evidence.

## Control and Audit Requirements
- Each routing decision must log: provider_selected, reason_code, latency_ms, token_estimate, fallback_chain_attempted.
- Any policy write touching deploy/infra/security boundaries requires explicit human approval before merge/execute.
- Unknown routing state defaults to blocked.

## Rollout
- Phase 1: advisory logging only.
- Phase 2: enforce ordered selection and fallback triggers.
- Phase 3: weighted balancing across subscription paths to prevent over-concentration.

## Rollback
- For pushed/shared changes use `git revert`.
- Preserve evidence artifacts and decision trail.

## References
- Onboarding policy: `/Users/kennethjones/Documents/Onboarding-ChatGPT-Codex.json`
- Issue: `docs/governance/github-artifacts/issues/2026-02-26-cio-proposal-001-subscription-first-routing.md`

