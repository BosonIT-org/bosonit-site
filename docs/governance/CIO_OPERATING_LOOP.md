# CIO Operating Loop

## Interface
GitHub is the system of record.

## Loop
Issue -> Design Note -> PR -> Evidence -> Decision Log

## Labels
- innovation-proposal
- experiment
- scale-candidate
- rejected-with-rationale

## Promotion Rule
Any promotion to scale-candidate requires an evidence link stored in Habitat Observatory (or a justified exception in the decision log).

## Approval Gate
Changes affecting deploy/infra/security (`ansible/`, `infra/`, `ops/windmill/`, `ops/governance/`, `.github/workflows/`) require label `human-approval-required` and approval by `ai-ops` (or designated approver).
