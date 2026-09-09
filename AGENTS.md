# Repository working instructions

Read docs/STATE.md, docs/DEBUGGING.md and docs/CODEX.md before editing.
Use docs/MODEL_STRATEGY.md on every task: Terra/medium routine execution,
Luna/low for worthwhile bounded documentation work, Astra/medium only for hard
evidence-backed decisions. At most one independent worker, no recursion; only
the lead controls devices or their disks. Follow the actual tool contract.

Inspect Git status and checkpoint before moving files. Preserve unrelated edits,
working functionality and downloaded Android/VM assets. The real CLI is
android_lab/cli.py, installed as lab via root pyproject.toml. Use uv sync --extra
test, uv run lab --help, and the full tests/ suite. Keep output in artifacts/;
use artifacts/tmp for Windows Temp problems. Run tools/windows/Test-Profiles.ps1
after script changes and tools/verify_repository.py plus git diff --check.

Keep API 36 clean; select AVD by name/serial. Do not repatch API 34 for its
reported translation SIGILL. Do not run archived identity/concealment/integrity
proposals as compatibility fixes. Archive is reference-only; no active Android
app module exists. Mocked checks are not live Proxmox/device proof.

Before any experiment read experiments/EXPERIMENT_LOG.md. After each attempt
append date, environment, hypothesis, one changed variable, exact command/action,
exit code, observed result, evidence paths and next decision. Distinguish verified,
reported, failed, inconclusive and not-run outcomes. Put raw/private data only in
artifacts/. Update docs/STATE.md when findings change. Never invent missing logs.
