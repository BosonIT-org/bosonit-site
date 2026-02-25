from __future__ import annotations

import json
import re
from enum import Enum

from pydantic import BaseModel, ConfigDict


class ConservationStatus(str, Enum):
    IMPROVED = "IMPROVED"
    DEGRADED = "DEGRADED"
    NEUTRAL = "NEUTRAL"


class InvasiveSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTINCTION_LEVEL = "EXTINCTION_LEVEL"


class RegulatoryVerdict(str, Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class InvasivePattern(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern_name: str
    severity: InvasiveSeverity
    remediation_suggestion: str


class HabitatImpactAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conservation_status_change: ConservationStatus
    critical_habitat_interference: bool
    mitigation_plan_verified: bool
    invasive_pattern_detection: list[InvasivePattern]
    regulatory_verdict: RegulatoryVerdict


def fallback_assessment() -> HabitatImpactAssessment:
    return HabitatImpactAssessment(
        conservation_status_change=ConservationStatus.NEUTRAL,
        critical_habitat_interference=False,
        mitigation_plan_verified=False,
        invasive_pattern_detection=[],
        regulatory_verdict=RegulatoryVerdict.REQUIRE_APPROVAL,
    )


def extract_json_payload(raw_text: str) -> str:
    stripped = raw_text.strip()

    fenced = re.findall(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        stripped = fenced[0].strip()

    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in assistant response.")
    return stripped[start : end + 1]


def parse_assessment_text(raw_text: str) -> HabitatImpactAssessment:
    payload = extract_json_payload(raw_text)
    parsed = json.loads(payload)
    return HabitatImpactAssessment.model_validate(parsed)

