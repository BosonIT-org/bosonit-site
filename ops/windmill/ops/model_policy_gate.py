#!/usr/bin/env python3
"""Policy gate for routing decisions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "ops/governance/model_role_registry.json"

NORMAL_REASONS = {"normal", "healthy", "primary_available"}


def load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def evaluate(decision: Dict[str, Any], registry: Dict[str, Any]) -> Dict[str, Any]:
    violations: List[str] = []
    required_controls: List[str] = []

    fallback = registry.get("fallback_policy", {})
    allowed = set(fallback.get("allowed_triggers", []))
    denied = set(fallback.get("denied_triggers", []))
    fallback_targets = set(fallback.get("fallback_targets", []))
    default_on_unknown = registry.get("default_on_unknown", "block")

    required_telemetry = list(registry.get("required_decision_telemetry", []))
    missing_telemetry = [k for k in required_telemetry if decision.get(k) in (None, "", [])]
    if missing_telemetry:
        violations.append("missing_required_telemetry:" + ",".join(missing_telemetry))

    reason_code = str(decision.get("reason_code", "unknown_reason"))
    provider_selected = decision.get("provider_selected")
    provider_source = decision.get("provider_source")
    selector_verdict = decision.get("verdict")
    impact_level = decision.get("impact_level", "advisory")
    human_approval_granted = bool(decision.get("human_approval_granted", False))

    approval_impacts = set(
        (registry.get("human_approval_gate", {}) or {}).get("required_for_impact", [])
    )
    if impact_level in approval_impacts and not human_approval_granted:
        violations.append(f"human_approval_required_for_impact:{impact_level}")
        required_controls.append("explicit_human_approval")

    if reason_code in denied:
        violations.append(f"denied_trigger:{reason_code}")
    elif reason_code not in allowed and reason_code not in NORMAL_REASONS and default_on_unknown == "block":
        violations.append(f"unknown_trigger_blocked:{reason_code}")

    if provider_source == "fallback" and reason_code not in allowed:
        violations.append("fallback_without_allowed_trigger")

    if provider_selected in fallback_targets and reason_code not in allowed:
        violations.append("fallback_target_selected_without_allowed_trigger")

    if selector_verdict not in ("allow", None):
        violations.append(f"selector_not_allow:{selector_verdict}")

    if any(v.startswith("denied_trigger:") or v.startswith("fallback_") for v in violations):
        policy_verdict = "deny"
    elif violations:
        policy_verdict = "require_approval"
    else:
        policy_verdict = "allow"

    approval_required = policy_verdict != "allow"
    return {
        "policy_verdict": policy_verdict,
        "policy_pass": policy_verdict == "allow",
        "approval_required": approval_required,
        "required_controls": required_controls,
        "violations": violations,
        "policy_id": registry.get("policy_id"),
        "default_on_unknown": default_on_unknown,
        "decision": decision,
    }


def read_decision(path: str | None) -> Dict[str, Any]:
    if path:
        return load_json(Path(path))
    if sys.stdin.isatty():
        return {}
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("STDIN decision must be JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Policy gate for model routing decisions")
    parser.add_argument("--decision-file", default=None)
    parser.add_argument("--registry-path", default=str(REGISTRY_PATH))
    parser.add_argument("--output-file", default=None)
    args = parser.parse_args()

    decision = read_decision(args.decision_file)
    registry = load_json(Path(args.registry_path))
    result = evaluate(decision, registry)

    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output_file:
        Path(args.output_file).write_text(payload + "\n")
    print(payload)
    return 0 if result.get("policy_pass") else 42


if __name__ == "__main__":
    raise SystemExit(main())
