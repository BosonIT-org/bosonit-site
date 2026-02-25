# Codex OAuth Runner Guide

This repository's Habitat Warden runs through `codex app-server` and expects a persistent OAuth login on a dedicated self-hosted runner.

## Scope

- Repository: `/Users/kennethjones/bosonit.org`
- Workflow: `.github/workflows/habitat-warden.yml`
- Runner labels: `self-hosted`, `codex-oauth`
- Default mode: `advisory`

## Dual-Project Context

- OAuth workflow is the authoritative primary project.
- Docker workflow is a concurrent canary project:
  - `.github/workflows/habitat-warden-docker.yml`
- Operating contract:
  - `/Users/kennethjones/bosonit.org/docs/habitat-warden-dual-project-contract.md`

## Phase 1: OAuth-First Bootstrap

1. Provision a persistent Linux self-hosted runner.
2. Attach labels:
- `self-hosted`
- `codex-oauth`
3. Install Codex CLI on the runner host.
4. Login once as the runner service identity:
```bash
codex login --device-auth
```
5. Confirm session:
```bash
codex login status
```
6. Ensure runner home persists:
- `~/.codex/config.toml`
- OAuth tokens under `~/.codex/`
7. Restrict runner usage:
- pin to this repo or trusted org workflows only
- keep shell/network controls in runner hardening policy

## Workflow Controls

- Advisory mode (default): `WARDEN_ENFORCEMENT_MODE=advisory`
- Enforce mode: `WARDEN_ENFORCEMENT_MODE=enforce`
- Model override: `CODEX_WARDEN_MODEL`

## Critical Habitat v1

The deterministic policy gate treats these as critical:

- `^\\.github/workflows/`
- `^stackcp/`
- `^deploy\\.sh$`

## API-Key Migration (Scale Phase)

Transport and script logic stay unchanged. Only auth bootstrap changes.

1. Add secret in runner environment:
```bash
export OPENAI_API_KEY=...
```
2. Login via API key:
```bash
printenv OPENAI_API_KEY | codex login --with-api-key
```
3. Verify:
```bash
codex login status
```
4. Optional cutover pattern:
- keep a separate runner label (for example `codex-apikey`)
- update `runs-on` in workflow once validated

## Operational Notes

- If app-server requests unexpected approvals/tool calls, the warden client returns conservative denials and fails safe to `REQUIRE_APPROVAL`.
- `assessment.json` is always uploaded as a workflow artifact.
- GitHub outputs emitted by the script:
- `regulatory_verdict`
- `requires_approval`
- `denial_reason`
- `assessment_json`
- `policy_mode`
- `should_block`
