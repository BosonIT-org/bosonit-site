# CIO Proposal 001: Layered Commit Sequence (L1-L4)

## Policy
- L0 optional cleanup is excluded.
- Exactly 4 required implementation commits.
- Keep commits small, scoped, and reversible.

## L1 - Governance Contract
### Commit message
`feat(governance): define subscription-first routing contract and fallback triggers`

### Files
- `/Users/kennethjones/bosonit.org/ops/governance/model_role_registry.json`

### Exit criteria
- Provider order and trigger allow/deny lists are explicit.
- `default_on_unknown=block` is set.

## L2 - Selector and Cost Governor Logic
### Commit message
`feat(routing): enforce subscription-first selector and allowed fallback triggers`

### Files
- `/Users/kennethjones/bosonit.org/ops/governance/scripts/agent_cost_governor.py`
- `/Users/kennethjones/bosonit.org/ops/windmill/ops/model_role_selector.py`

### Exit criteria
- Selector returns deterministic decision payload.
- Fallback only occurs for allowed triggers.
- Unknown trigger blocks.

## L3 - Windmill Gate and Runtime Contract
### Commit message
`feat(windmill): add strict policy gate and script contracts for routing decisions`

### Files
- `/Users/kennethjones/bosonit.org/ops/windmill/ops/model_role_selector.script.yaml`
- `/Users/kennethjones/bosonit.org/ops/windmill/ops/model_policy_gate.py`
- `/Users/kennethjones/bosonit.org/ops/windmill/ops/model_policy_gate.script.yaml`

### Exit criteria
- Gate rejects denied/unknown reasons.
- Script defaults do not permit silent downgrade.
- Fail-closed behavior is explicit.

## L4 - Evidence and Decision Closure
### Commit message
`docs(governance): attach routing evidence traces and finalize decision record`

### Files
- `/Users/kennethjones/bosonit.org/docs/governance/evidence/2026-02-26/cio-proposal-001-subscription-first-routing/IMPLEMENTATION-EVIDENCE-TEMPLATE.md`
- `/Users/kennethjones/bosonit.org/docs/decisions/ADR-2026-02-26-cio-proposal-001-routing-implementation.md`

### Exit criteria
- Trace set is complete (primary, allowed fallbacks, denied fallback).
- Required check results are recorded.
- ADR status can move from `Proposed` to `Accepted` after approval and passing checks.

## Hard Stop Rules
- If scope expands into deploy/infra/security-impacting execution, stop and require explicit human approval.
- If secrets are detected, stop, remediate, and follow incident rollback policy.
