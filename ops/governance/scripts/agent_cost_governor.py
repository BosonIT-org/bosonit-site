#!/usr/bin/env python3
"""BosonIT routing governor for subscription-first model selection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Set

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "model_role_registry.json"
NORMAL_REASONS = {"normal", "healthy", "primary_available"}


def load_registry(path: Path) -> Dict[str, Any]:
    registry = json.loads(path.read_text())
    if "provider_order" not in registry or "fallback_policy" not in registry:
        raise ValueError("Registry missing required keys: provider_order/fallback_policy")
    return registry


def _load_json_file(path: Optional[Path]) -> Dict[str, Any]:
    if not path:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object for availability data")
    return data


def _is_available(availability: Dict[str, Any], provider_id: str) -> bool:
    raw = availability.get(provider_id, True)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, dict):
        return bool(raw.get("available", True))
    return bool(raw)


def _first_available(
    candidates: Iterable[str],
    availability: Dict[str, Any],
    excluded: Optional[Set[str]] = None,
) -> Optional[str]:
    excluded = excluded or set()
    for candidate in candidates:
        if candidate in excluded:
            continue
        if _is_available(availability, candidate):
            return candidate
    return None


def _blocked_decision(
    registry: Dict[str, Any],
    reason_code: str,
    token_estimate: int,
    latency_ms: Optional[int],
    block_reason: str,
) -> Dict[str, Any]:
    return {
        "verdict": "require_approval",
        "approval_required": True,
        "provider_selected": None,
        "provider_source": "blocked",
        "reason_code": reason_code,
        "fallback_chain_attempted": [],
        "token_estimate": int(token_estimate),
        "latency_ms": latency_ms,
        "policy_id": registry.get("policy_id"),
        "policy_status": registry.get("policy_status", "unknown"),
        "block_reason": block_reason,
    }


def decide_route(
    registry: Dict[str, Any],
    reason_code: str = "normal",
    impact_level: str = "advisory",
    active_provider: Optional[str] = None,
    availability: Optional[Dict[str, Any]] = None,
    token_estimate: int = 0,
    latency_ms: Optional[int] = None,
) -> Dict[str, Any]:
    availability = availability or {}
    reason_code = reason_code or "normal"

    order = [provider["id"] for provider in registry.get("provider_order", []) if provider.get("id")]
    fallback_policy = registry.get("fallback_policy", {})
    allowed = set(fallback_policy.get("allowed_triggers", []))
    denied = set(fallback_policy.get("denied_triggers", []))
    fallback_targets = list(fallback_policy.get("fallback_targets", []))

    approval_impacts = set(
        (registry.get("human_approval_gate", {}) or {}).get("required_for_impact", [])
    )
    if impact_level in approval_impacts:
        return _blocked_decision(
            registry,
            reason_code=reason_code,
            token_estimate=token_estimate,
            latency_ms=latency_ms,
            block_reason=f"impact_level_requires_human_approval:{impact_level}",
        )

    if reason_code in denied:
        return _blocked_decision(
            registry,
            reason_code=reason_code,
            token_estimate=token_estimate,
            latency_ms=latency_ms,
            block_reason=f"fallback_trigger_denied:{reason_code}",
        )

    known_reason = reason_code in NORMAL_REASONS or reason_code in allowed
    if not known_reason and registry.get("default_on_unknown") == "block":
        return _blocked_decision(
            registry,
            reason_code=reason_code,
            token_estimate=token_estimate,
            latency_ms=latency_ms,
            block_reason=f"unknown_reason_blocked:{reason_code}",
        )

    excluded = set()
    if reason_code in allowed:
        if not active_provider and order:
            active_provider = order[0]
        if active_provider:
            excluded.add(active_provider)

    fallback_chain_attempted = [provider for provider in order if provider not in excluded]
    provider_selected = _first_available(order, availability, excluded)

    if not provider_selected and reason_code in allowed:
        provider_selected = _first_available(fallback_targets, availability)
        fallback_chain_attempted.extend(fallback_targets)

    if not provider_selected:
        return _blocked_decision(
            registry,
            reason_code=reason_code,
            token_estimate=token_estimate,
            latency_ms=latency_ms,
            block_reason="no_provider_available",
        )

    provider_source = "subscription" if provider_selected in order else "fallback"
    return {
        "verdict": "allow",
        "approval_required": False,
        "provider_selected": provider_selected,
        "provider_source": provider_source,
        "reason_code": reason_code,
        "fallback_chain_attempted": fallback_chain_attempted,
        "token_estimate": int(token_estimate),
        "latency_ms": latency_ms,
        "policy_id": registry.get("policy_id"),
        "policy_status": registry.get("policy_status", "unknown"),
        "block_reason": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="BosonIT subscription-first routing governor")
    parser.add_argument("--registry-path", default=str(DEFAULT_REGISTRY_PATH))
    parser.add_argument("--reason-code", default="normal")
    parser.add_argument("--impact-level", default="advisory")
    parser.add_argument("--active-provider", default=None)
    parser.add_argument("--availability-file", default=None)
    parser.add_argument("--token-estimate", type=int, default=0)
    parser.add_argument("--latency-ms", type=int, default=None)
    parser.add_argument("--output-file", default=None)
    args = parser.parse_args()

    registry = load_registry(Path(args.registry_path))
    availability = _load_json_file(Path(args.availability_file)) if args.availability_file else {}

    decision = decide_route(
        registry=registry,
        reason_code=args.reason_code,
        impact_level=args.impact_level,
        active_provider=args.active_provider,
        availability=availability,
        token_estimate=args.token_estimate,
        latency_ms=args.latency_ms,
    )

    payload = json.dumps(decision, indent=2, sort_keys=True)
    if args.output_file:
        Path(args.output_file).write_text(payload + "\n")
    print(payload)

    return 0 if decision.get("verdict") == "allow" else 42


if __name__ == "__main__":
    raise SystemExit(main())
