from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from habitat_models import (  # noqa: E402
    RegulatoryVerdict,
    fallback_assessment,
    parse_assessment_text,
)


def test_parse_assessment_text_from_json_fence() -> None:
    raw = """```json
{
  "conservation_status_change": "NEUTRAL",
  "critical_habitat_interference": false,
  "mitigation_plan_verified": true,
  "invasive_pattern_detection": [],
  "regulatory_verdict": "APPROVE"
}
```"""
    parsed = parse_assessment_text(raw)
    assert parsed.regulatory_verdict == RegulatoryVerdict.APPROVE
    assert parsed.critical_habitat_interference is False


def test_fallback_assessment_is_require_approval() -> None:
    parsed = fallback_assessment()
    assert parsed.regulatory_verdict == RegulatoryVerdict.REQUIRE_APPROVAL

