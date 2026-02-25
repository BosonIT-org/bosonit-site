# Habitat Warden Focus Pack

## Objective
Keep Habitat Warden aligned to mission value while minimizing PR friction across both concurrent projects.

## Dual-project model
- OAuth Primary (authoritative): `/Users/kennethjones/bosonit.org/.github/workflows/habitat-warden.yml`
- Docker Canary (concurrent validation): `/Users/kennethjones/bosonit.org/.github/workflows/habitat-warden-docker.yml`
- Contract: `/Users/kennethjones/bosonit.org/docs/habitat-warden-dual-project-contract.md`

## What is monitored every run
- Run health (`GREEN` | `YELLOW` | `RED`)
- Fallback detection (`fail-safe fallback` events)
- Timeout detection
- Rolling fallback rate over latest 50 runs
- Rolling timeout rate over latest 50 runs
- Rolling error-run rate over latest 50 runs
- SLO pass/fail by project-specific SLO config

## OAuth Primary runtime outputs
- Assessment: `/tmp/assessment.json`
- Warden log: `/tmp/habitat-warden.log`
- Scorecard JSON: `/tmp/habitat-warden-scorecard.json`
- Scorecard markdown: `/tmp/habitat-warden-scorecard.md`
- History tail snapshot: `/tmp/habitat-warden-history-tail.json`
- Rolling history path: `/var/tmp/habitat-warden/history.jsonl`
- SLO config: `/Users/kennethjones/bosonit.org/.github/codex/habitat-warden-slo.json`

## Docker Canary runtime outputs
- Assessment: `/tmp/habitat-warden-docker/assessment.json`
- Warden log: `/tmp/habitat-warden-docker/habitat-warden.log`
- Scorecard JSON: `/tmp/habitat-warden-docker-scorecard.json`
- Scorecard markdown: `/tmp/habitat-warden-docker-scorecard.md`
- History tail snapshot: `/tmp/habitat-warden-docker-history-tail.json`
- Rolling history path: `/var/tmp/habitat-warden/docker-history.jsonl`
- SLO config: `/Users/kennethjones/bosonit.org/.github/codex/habitat-warden-docker-slo.json`

## Operating target
- Prevent unsafe infra/deploy changes from merging in authoritative mode.
- Keep friction low during advisory calibration in both projects.
- Promote canary capabilities only after documented SLO stability and governance approval.
