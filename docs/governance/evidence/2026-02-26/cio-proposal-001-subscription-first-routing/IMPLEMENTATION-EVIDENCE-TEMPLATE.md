# Implementation Evidence Template: Proposal 001 Routing

## Metadata
- `timestamp_utc`: `2026-02-26T00:00:00Z`
- `operator`: `codex`
- `branch`: `codex/cio-proposal-001-implementation`
- `commit_sha`: `pending`

## Policy Version
- `policy_version`: `subscription-first-routing`
- `selector_version`: `model_role_selector`

## Trace 1: Primary Route
- `provider_selected`: `openai-codex`
- `reason_code`: `normal`
- `latency_ms`: `180`
- `token_estimate`: `1200`
- `fallback_chain_attempted`: `["openai-codex","gemini-pro","claude-opus","claude-sonnet"]`

## Trace 2: Allowed Fallback (rate_limit)
- `provider_selected`: `gemini-pro`
- `reason_code`: `rate_limit`
- `latency_ms`: `260`
- `token_estimate`: `1300`
- `fallback_chain_attempted`: `["gemini-pro","claude-opus","claude-sonnet"]`

## Trace 3: Allowed Fallback (provider_outage)
- `provider_selected`: `claude-opus`
- `reason_code`: `provider_outage`
- `latency_ms`: `340`
- `token_estimate`: `1250`
- `fallback_chain_attempted`: `["openai-codex","claude-opus","claude-sonnet"]`

## Trace 4: Allowed Fallback (quota_exhausted)
- `provider_selected`: `cerebras-proxy`
- `reason_code`: `quota_exhausted`
- `latency_ms`: `520`
- `token_estimate`: `1400`
- `fallback_chain_attempted`: `["openai-codex","gemini-pro","claude-sonnet","cerebras-proxy","local-mesh"]`

## Trace 5: Denied Trigger
- `provider_selected`: `null`
- `reason_code`: `manual_preference`
- `blocked`: `true`
- `block_message`: `fallback_trigger_denied:manual_preference`
- `policy_gate_verdict`: `deny`

## Required Check Results
- `security / gitleaks`: `pending_in_github_pr (local gitleaks not installed in this workspace)`
- `policy / habitat-guardrails`: `local_policy_gate_validated`
- `ci / test`: `pending_in_github_pr`

## Rollback Record
- `rollback_needed`: `false`
- `rollback_command`: `n/a`
- `rollback_outcome`: `n/a`

## Controlled Dry-Run Artifacts
- selector output: `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/selector-primary.json`
- policy gate output: `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/policy-primary.json`
- policy gate verdict: `allow`
- policy pass: `true`
- violations: `[]`
- selector output: `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/selector-rate-limit.json`
- policy gate output: `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/policy-rate-limit.json`
- selector output: `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/selector-provider-outage.json`
- policy gate output: `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/policy-provider-outage.json`
- selector output: `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/selector-quota-exhausted.json`
- policy gate output: `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/policy-quota-exhausted.json`
- selector output: `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/selector-denied-trigger.json`
- policy gate output: `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/policy-denied-trigger.json`
