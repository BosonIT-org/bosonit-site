from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from habitat_models import (  # noqa: E402
    ConservationStatus,
    HabitatImpactAssessment,
    InvasivePattern,
    InvasiveSeverity,
    RegulatoryVerdict,
)
from habitat_policy import PolicyConfig, apply_policy  # noqa: E402


def _default_policy(mode: str = "advisory") -> PolicyConfig:
    return PolicyConfig(
        mode=mode,
        critical_habitat_regex=[r"^\.github/workflows/", r"^stackcp/", r"^deploy\.sh$"],
        deny_on_extinction_level=True,
        require_approval_on_unmitigated_critical_change=True,
    )


def test_extinction_level_forces_deny() -> None:
    assessment = HabitatImpactAssessment(
        conservation_status_change=ConservationStatus.DEGRADED,
        critical_habitat_interference=False,
        mitigation_plan_verified=True,
        invasive_pattern_detection=[
            InvasivePattern(
                pattern_name="hardcoded-secret",
                severity=InvasiveSeverity.EXTINCTION_LEVEL,
                remediation_suggestion="Move secret to vault.",
            )
        ],
        regulatory_verdict=RegulatoryVerdict.APPROVE,
    )
    decision = apply_policy(assessment, ["src/app.ts"], _default_policy(mode="enforce"))
    assert decision.final_verdict == RegulatoryVerdict.DENY
    assert decision.should_block is True


def test_unmitigated_critical_change_requires_approval() -> None:
    assessment = HabitatImpactAssessment(
        conservation_status_change=ConservationStatus.NEUTRAL,
        critical_habitat_interference=True,
        mitigation_plan_verified=False,
        invasive_pattern_detection=[],
        regulatory_verdict=RegulatoryVerdict.APPROVE,
    )
    decision = apply_policy(
        assessment, [".github/workflows/deploy.yml"], _default_policy(mode="enforce")
    )
    assert decision.final_verdict == RegulatoryVerdict.REQUIRE_APPROVAL
    assert decision.requires_approval is True
    assert decision.should_block is True


def test_noncritical_change_keeps_model_verdict() -> None:
    assessment = HabitatImpactAssessment(
        conservation_status_change=ConservationStatus.IMPROVED,
        critical_habitat_interference=True,
        mitigation_plan_verified=False,
        invasive_pattern_detection=[],
        regulatory_verdict=RegulatoryVerdict.APPROVE,
    )
    decision = apply_policy(assessment, ["src/pages/index.astro"], _default_policy(mode="advisory"))
    assert decision.final_verdict == RegulatoryVerdict.APPROVE
    assert decision.should_block is False

