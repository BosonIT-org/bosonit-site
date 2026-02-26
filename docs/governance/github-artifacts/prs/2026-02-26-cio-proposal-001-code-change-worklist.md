# CIO Proposal 001: Exact Code-Change Worklist

## Objective
Implement subscription-first routing with deterministic fallback and fail-closed policy enforcement.

## Guardrails
- No deploy, infra mutation, or security-impacting execution without explicit human approval.
- Unknown routing state must block.
- Required checks must pass: `security / gitleaks`, `policy / habitat-guardrails`, `ci / test`.

## File-by-File Worklist
1. `/Users/kennethjones/bosonit.org/ops/governance/model_role_registry.json`
- Add canonical provider order for subscription-first selection.
- Add allowed fallback triggers: `rate_limit`, `provider_outage`, `quota_exhausted`.
- Add denied triggers: `manual_preference`, `silent_downgrade`, `unknown_reason`.
- Add `default_on_unknown=block`.

2. `/Users/kennethjones/bosonit.org/ops/governance/scripts/agent_cost_governor.py`
- Enforce provider precedence from registry.
- Permit fallback only on allowed triggers.
- Add optional weighted rotation that still respects policy order.
- Emit structured decision fields: `provider_selected`, `reason_code`, `fallback_chain_attempted`, `token_estimate`.

3. `/Users/kennethjones/bosonit.org/ops/windmill/ops/model_role_selector.py`
- Implement selector decision graph using registry contract.
- Return deterministic error state for unknown trigger and block by default.
- Attach telemetry fields required by evidence template.

4. `/Users/kennethjones/bosonit.org/ops/windmill/ops/model_role_selector.script.yaml`
- Expose inputs for provider availability, quota/rate-limit status, and override policy flags.
- Ensure defaults do not allow silent fallback.

5. `/Users/kennethjones/bosonit.org/ops/windmill/ops/model_policy_gate.py`
- Validate decision output against policy.
- Block unknown or denied fallback triggers.
- Require approval path if change class escalates into deploy/infra/security impact.

6. `/Users/kennethjones/bosonit.org/ops/windmill/ops/model_policy_gate.script.yaml`
- Encode gate metadata and strict failure behavior.
- Keep script scope limited to routing policy enforcement.

7. `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/IMPLEMENTATION-EVIDENCE-TEMPLATE.md`
- Populate with real traces for normal path, each allowed fallback, and one blocked denied trigger.
- Record required check outcomes and rollback status.

## Done Criteria for This Worklist
- All listed files updated with no scope drift.
- Decision telemetry present and evidence template populated.
- Unknown state blocks.
- Required checks pass.
