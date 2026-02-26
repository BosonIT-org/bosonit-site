#!/usr/bin/env python3
"""Windmill-facing selector for BosonIT subscription-first model routing."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "ops/governance/model_role_registry.json"
GOVERNANCE_SCRIPTS_PATH = REPO_ROOT / "ops/governance/scripts"

if str(GOVERNANCE_SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(GOVERNANCE_SCRIPTS_PATH))

from agent_cost_governor import decide_route, load_registry  # noqa: E402


def _read_request(path: str | None) -> Dict[str, Any]:
    if path:
        data = json.loads(Path(path).read_text())
        if not isinstance(data, dict):
            raise ValueError("Request file must contain a JSON object")
        return data

    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("STDIN request must be a JSON object")
            return data
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Model role selector")
    parser.add_argument("--request-file", default=None)
    parser.add_argument("--registry-path", default=str(DEFAULT_REGISTRY_PATH))
    parser.add_argument("--output-file", default=None)
    args = parser.parse_args()

    request = _read_request(args.request_file)
    registry = load_registry(Path(args.registry_path))

    decision = decide_route(
        registry=registry,
        reason_code=request.get("reason_code", "normal"),
        impact_level=request.get("impact_level", "advisory"),
        active_provider=request.get("active_provider"),
        availability=request.get("availability", {}),
        token_estimate=int(request.get("token_estimate", 0)),
        latency_ms=request.get("latency_ms"),
    )
    decision["selector"] = "model_role_selector"
    decision["request_id"] = request.get("request_id")

    payload = json.dumps(decision, indent=2, sort_keys=True)
    if args.output_file:
        Path(args.output_file).write_text(payload + "\n")
    print(payload)

    return 0 if decision.get("verdict") == "allow" else 42


if __name__ == "__main__":
    raise SystemExit(main())
