# Habitat Warden Dual-Project Contract

## Purpose
Define two concurrent Habitat Warden projects with explicit authority, boundaries, and observability.

## Project A: OAuth Primary (Authoritative)
- Workflow: `.github/workflows/habitat-warden.yml`
- Runner labels: `self-hosted`, `codex-oauth`
- Role: `primary`
- Merge governance authority:
  - advisory mode: report only
  - enforce mode: authoritative merge blocking
- SLO config: `.github/codex/habitat-warden-slo.json`
- Rolling history: `/var/tmp/habitat-warden/history.jsonl`

## Project B: Docker Canary (Concurrent Validation)
- Workflow: `.github/workflows/habitat-warden-docker.yml`
- Runner labels: `self-hosted`, `linux`, `bmos-svr0`
- Role: `canary`
- Merge governance authority:
  - default is advisory
  - enforcement is disabled unless explicitly unlocked
- SLO config: `.github/codex/habitat-warden-docker-slo.json`
- Rolling history: `/var/tmp/habitat-warden/docker-history.jsonl`

## Guardrails
- Concurrency isolation:
  - OAuth group: `habitat-warden-oauth-<pr-or-ref>`
  - Docker group: `habitat-warden-docker-<pr-or-ref>`
- Docker enforcement guard:
  - requires both `WARDEN_ENFORCEMENT_MODE=enforce` and `WARDEN_ALLOW_ENFORCEMENT=true`
  - otherwise emits warning and remains non-blocking
- OAuth enforcement guard:
  - enforce path only active when `WARDEN_PROJECT_ROLE=primary`

## Required Outputs Per Project
- `assessment.json`
- structured GitHub outputs (`regulatory_verdict`, `requires_approval`, `denial_reason`, `assessment_json`)
- scorecard JSON and markdown
- rolling history tail artifact

## Promotion / Cutover Rule
- Docker canary can be promoted to authoritative only after:
  - stable SLO pass rate over agreed window
  - documented false-positive review
  - explicit governance decision in records management

## Change Control
- Any change to model, timeout, policy, or enforcement flags must update:
  - workflow env in the target project
  - corresponding SLO/policy documentation
  - configuration record in Ansible/Windmill/Vault inventory pipeline
