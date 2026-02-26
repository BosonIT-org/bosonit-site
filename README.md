# BosonIT Site Repository

This repository is the customer-facing and application delivery surface for BosonIT.

## Role in the three-repo habitat
- `BosonIT-org/bosonit-site`: product and delivery surface (this repo)
- `BosonIT-org/bosonit-habitat-core`: governance, policy, control-plane workflows
- `BosonIT-org/bosonit-habitat-observatory`: evidence, observability, records

## Operating boundary
- Deploy and app changes belong here.
- Governance contracts and global policy definitions belong in habitat-core.
- Evidence artifacts and observatory records belong in habitat-observatory.

## PR and governance expectations
- All changes go through branch -> PR -> required checks -> merge.
- Sensitive path changes require delegated ai-ops gate and human approval label.
- Merge strategy is squash unless an approved ADR states otherwise.
