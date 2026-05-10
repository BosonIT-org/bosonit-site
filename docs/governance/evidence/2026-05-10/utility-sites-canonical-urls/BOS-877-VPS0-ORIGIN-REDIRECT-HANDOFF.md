# BOS-877 vps0 Origin Redirect Handoff

## Timestamp
- `2026-05-10T04:14:15Z`

## Scope
- issue: `BOS-877`
- objective: enable the BOS-121 legacy calculator `301` redirects on the `vps0` origin serving stack without widening the rest of the site payload

## What This Heartbeat Verified
- `cd /home/ken/bosonit-site && ./scripts/verify-bos-121-canonical-live.sh`
- current public state:
  - `/utility-sites/` returns `200`
  - `/mortgage-calculator/`, `/calorie-calculator/`, and `/sales-tax-calculator/` return `200`
  - public `observatory/utility-sites.latest.json` points `preview_url` at the short aliases
  - public `sitemap.xml` includes `/utility-sites/` plus the three short aliases
  - the three legacy `/utility-sites/...` calculator routes still return `200` instead of `301`
- verifier result:
  - failed with `6` issues
  - all `6` failures are the expected redirect/status gaps on the three legacy calculator routes

## Diagnostic Narrowing
- The BOS-121 content payload is mostly live.
- The remaining defect is now isolated to the origin redirect layer:
  - legacy route bodies are still being served as first-class pages
  - the public short routes, hub, sitemap, and observatory feed already reflect BOS-121
- This means a broad content republish is no longer the safest next step.
- The smallest governed fix is to patch only `/var/www/bosonit/.htaccess` on `vps0`, then rerun the existing live verifier.

## New Work Product
- script:
  - `scripts/enable-bos-877-vps0-legacy-redirects.sh`
- manual workflow:
  - `.github/workflows/bos-877-vps0-legacy-redirects.yml`
- clean patch packet:
  - `docs/governance/evidence/2026-05-10/utility-sites-canonical-urls/BOS-877-git-apply.patch`

## Script Intent
- connect to `vps0`
- create a rollback snapshot of `/var/www/bosonit/.htaccess`
- insert only the three BOS-121 legacy-to-short redirect rules if they are missing
- preserve the rest of the file as-is
- rerun `scripts/verify-bos-121-canonical-live.sh` unless `--skip-live-verify` is set

## Pilot Lane
- one host only: `vps0`
- one file only: `/var/www/bosonit/.htaccess`

## Release Ops Command
Run from a credentialed `bosonit-site` checkout:

```bash
cd /home/ken/bosonit-site
./scripts/enable-bos-877-vps0-legacy-redirects.sh
```

Optional inspection-only mode:

```bash
cd /home/ken/bosonit-site
./scripts/enable-bos-877-vps0-legacy-redirects.sh --print-remote
```

## GitHub Actions Lane
- If direct SSH from the operator runtime is unavailable, publish the new workflow file and trigger:
  - `BOS-877 vps0 Legacy Redirects`
- The workflow uses the existing `VPS0_HOST`, `VPS0_USER`, and `VPS0_SSH_KEY` GitHub repo secrets/vars to:
  - apply the one-file `.htaccess` patch
  - verify the rules exist on `vps0`
  - verify public `301` behavior unless `skip_public_edge_verify=true`

## Clean Publish Packet
- Because the current local `bosonit-site` worktree is noisy and unauthenticated, a clean patch packet is included for just the three BOS-877 files.
- Apply it from a clean `bosonit-site` checkout with:

```bash
cd /path/to/clean/bosonit-site
git apply /home/ken/bosonit-site/docs/governance/evidence/2026-05-10/utility-sites-canonical-urls/BOS-877-git-apply.patch
```

## Exit Criteria
- `/utility-sites/mortgage-payment-calculator/` returns `301` to `/mortgage-calculator/`
- `/utility-sites/calorie-deficit-calculator/` returns `301` to `/calorie-calculator/`
- `/utility-sites/sales-tax-calculator/` returns `301` to `/sales-tax-calculator/`
- `./scripts/verify-bos-121-canonical-live.sh` passes cleanly

## Rollback
- the script creates a rollback snapshot under:
  - `/var/www/bosonit/.rollback/BOS-877-<timestamp>/.htaccess.before`
- it prints the exact restore command after patching

## Unblock Owner And Action
- **Owner:** Release Ops / credentialed site deployer
  - **Action:** run `scripts/enable-bos-877-vps0-legacy-redirects.sh` from a credentialed `bosonit-site` execution surface and attach the successful verifier output back to `BOS-877`

## Governance Note
- `vps0` is still absent from the canonical runtime registry snapshot available in this workspace, but that registry drift is not required to execute this one-file redirect fix.
- Treat runtime-registry reconciliation as follow-on governance work rather than as a blocker to this scoped origin patch.
