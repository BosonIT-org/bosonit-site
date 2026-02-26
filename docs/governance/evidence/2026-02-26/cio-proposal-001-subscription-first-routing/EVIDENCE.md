# Evidence: CIO Proposal 001 - Subscription-First Routing

## Metadata
- `timestamp_utc`: `2026-02-26T00:00:00Z`
- `classification`: `innovation_governance`
- `status`: `proposal`
- `impact`: `advisory`

## Expected Runtime Signals
- `provider_selected`
- `reason_code`
- `latency_ms`
- `token_estimate`
- `fallback_chain_attempted`

## Required Trace Set
- Normal routing trace (Codex selected).
- Rate-limit fallback trace.
- Outage fallback trace.
- Quota exhaustion fallback trace.
- Blocked trace for disallowed trigger.

## Linked Artifacts
- Issue: `docs/governance/github-artifacts/issues/2026-02-26-cio-proposal-001-subscription-first-routing.md`
- Design Note: `docs/governance/design-notes/DN-2026-02-26-cio-proposal-001-subscription-first-routing.md`
- PR Artifact: `docs/governance/github-artifacts/prs/2026-02-26-cio-proposal-001-subscription-first-routing-pr.md`
- Decision Log: `docs/decisions/ADR-2026-02-26-cio-proposal-001-subscription-first-routing.md`
