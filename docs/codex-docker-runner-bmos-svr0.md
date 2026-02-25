# BosonIT Docker Warden Runner (bmos-svr0)

This document defines the concurrent Docker path for the Habitat Warden.

## Workflow

- Workflow file: `.github/workflows/habitat-warden-docker.yml`
- Runner labels: `self-hosted`, `linux`, `bmos-svr0`
- Mode default: `advisory`
- Critical habitat policy and schema are reused from:
- `.github/codex/habitat-policy.json`
- `.github/codex/schemas/hia-output.schema.json`

## Runtime model

- The job builds a minimal Python image from `.github/docker/warden/Dockerfile`.
- The container executes `.github/scripts/codex_warden_appserver.py`.
- Codex CLI auth uses OAuth state mounted from host runner home:
- Host path: `${HOME}/.codex`
- Container path: `/root/.codex`

## Required host prerequisites on bmos-svr0

- Docker Engine available to runner user.
- `codex` CLI installed on host and present in `PATH`.
- One-time OAuth bootstrap as runner service identity:

```bash
codex login --device-auth
codex login status
```

- Runner home persistence enabled so `${HOME}/.codex` survives jobs.

## Artifact outputs

- `/tmp/habitat-warden-docker/assessment.json`
- `/tmp/habitat-warden-docker/habitat-warden.log`

## Migration to API key auth

- Keep workflow and container flow unchanged.
- Replace OAuth bootstrap with API key login on runner host:

```bash
printenv OPENAI_API_KEY | codex login --with-api-key
```

