# Deprecated Or Reference-Only Material

Last updated: 2026-09-14

## Historical Handoff Recipes

The archived Proxmox/Bliss/root/module proposals are retained as historical
references. They are not executable authority and are not working outcomes.

Sources:

- `archive/historical-proposals/PROJECT_HANDOFF_SOURCE.md`
- `experiments/2026-09-09-user-proposal.md`
- `docs/DEBUGGING.md`

## API 34 Rooted Baseline For Pokemon GO Login

The rooted API 34 image can demonstrate Magisk `su`, but it is deprecated for
Pokemon GO login work because the target app hit native translation SIGILL.

Use it only for bounded root-tooling checks that explicitly do not claim app
compatibility.

## Generic FastAPI Fleet Service

The pasted FastAPI/PostgreSQL/Redis architecture is not part of the active
implementation. The current supported entry point is the `lab` CLI and the
standard-library Proxmox planner/deployer.

Add service infrastructure only after a demonstrated workflow needs it.
