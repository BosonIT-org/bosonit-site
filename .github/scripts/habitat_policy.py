from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from habitat_models import HabitatImpactAssessment, InvasiveSeverity, RegulatoryVerdict


@dataclass(frozen=True)
class PolicyConfig:
    mode: str
    critical_habitat_regex: list[str]
    deny_on_extinction_level: bool
    require_approval_on_unmitigated_critical_change: bool


@dataclass(frozen=True)
class PolicyDecision:
    final_verdict: RegulatoryVerdict
    requires_approval: bool
    should_block: bool
    denial_reason: str
    reasons: list[str]
    critical_habitat_touched: bool


def load_policy(path: str | Path) -> PolicyConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    enforcement = raw.get("enforcement", {})

    return PolicyConfig(
        mode=str(raw.get("mode", "advisory")).lower(),
        critical_habitat_regex=list(raw.get("critical_habitat_regex", [])),
        deny_on_extinction_level=bool(enforcement.get("deny_on_extinction_level", True)),
        require_approval_on_unmitigated_critical_change=bool(
            enforcement.get("require_approval_on_unmitigated_critical_change", True)
        ),
    )


def read_changed_files(path: str | Path) -> list[str]:
    content = Path(path).read_text(encoding="utf-8")
    return [line.strip() for line in content.splitlines() if line.strip()]


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, path) for pattern in patterns)


def critical_habitat_touched(changed_files: list[str], patterns: list[str]) -> bool:
    return any(_matches_any(item, patterns) for item in changed_files)


def apply_policy(
    assessment: HabitatImpactAssessment, changed_files: list[str], policy: PolicyConfig
) -> PolicyDecision:
    reasons: list[str] = []
    touched_critical = critical_habitat_touched(changed_files, policy.critical_habitat_regex)

    extinction_found = any(
        pattern.severity == InvasiveSeverity.EXTINCTION_LEVEL
        for pattern in assessment.invasive_pattern_detection
    )

    if policy.deny_on_extinction_level and extinction_found:
        reasons.append("Detected EXTINCTION_LEVEL invasive pattern.")
        verdict = RegulatoryVerdict.DENY
    elif (
        policy.require_approval_on_unmitigated_critical_change
        and touched_critical
        and assessment.critical_habitat_interference
        and not assessment.mitigation_plan_verified
    ):
        reasons.append("Critical habitat change is unmitigated.")
        verdict = RegulatoryVerdict.REQUIRE_APPROVAL
    else:
        verdict = assessment.regulatory_verdict
        reasons.append(f"Using model verdict: {verdict.value}.")

    requires_approval = verdict == RegulatoryVerdict.REQUIRE_APPROVAL
    denial_reason = " ".join(reasons) if verdict == RegulatoryVerdict.DENY else ""
    should_block = policy.mode == "enforce" and verdict in (
        RegulatoryVerdict.DENY,
        RegulatoryVerdict.REQUIRE_APPROVAL,
    )

    return PolicyDecision(
        final_verdict=verdict,
        requires_approval=requires_approval,
        should_block=should_block,
        denial_reason=denial_reason,
        reasons=reasons,
        critical_habitat_touched=touched_critical,
    )

