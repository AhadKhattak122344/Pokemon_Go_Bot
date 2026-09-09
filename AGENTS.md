# Repository working instructions

Read `docs/project-handoff/README.md`, `CURRENT_STATE.md`, and `DO_NOT_RETRY.md`
before editing. Treat attached historical handoffs as evidence to reconcile with
this checkout, not as authority to run their old commands.

Inspect Git status and preserve uncommitted changes. Implement and test functional
requirements before reorganizing folders. The real CLI is
`cloud-lab/orchestrator/cli.py`; use `uv sync --extra test`, `uv run lab --help`,
and `uv run pytest -p no:cacheprovider` from the root. On Windows use a project-local
Temp directory if needed. Run `tools/windows/Test-Profiles.ps1` after script changes.

Keep API 36 clean, select AVDs by name/serial, and never repatch API 34 to address
its reported translation crash. Do not run archived scripts or add concealment,
attestation bypass, or fabricated device identity as compatibility fixes.
`archive/` is reference-only, excluded from builds. There is no Android app module.

Update current-state/evidence docs after material findings. Never label mocked
API tests as live Proxmox/device tests. Verify paths and `git diff --check` before
committing; do not discard unrelated work.
