# Governance Templates

## Issue Template
**Hypothesis:**

**Expected Value:**

**KPI (baseline -> target):**

**Risk Class:** R0-docs | R1-nonprod | R2-prod-safe | R3-prod-sensitive | R4-restricted-deploy

**Owner:**

## Design Note Template (docs/design/<issue-id>-<slug>.md)
- Context
- Constraints
- Options
- Decision
- Acceptance Criteria
- Risks

## PR Template Sections
- Hypothesis
- Expected Value
- KPI
- Risk Class
- Rollback Plan
- Owner
- Evidence Link
- Decision Log Link
- Changed Paths Summary

## Evidence Record Template (observatory/evidence/YYYY-MM-DD/<issue-or-pr-id>/record.json)
{
  "timestamp_utc": "",
  "kpi": "",
  "delta": 0,
  "method": "",
  "decision_ref": ""
}

## ADR Template
See docs/decisions/ADR-TEMPLATE.md
