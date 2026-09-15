# Android VM Lab

Python CLI and Windows-native Android emulator tools for authorized APK testing,
with optional Linux Docker and Proxmox template-clone support. Working behavior
is preserved; there is no active Android app/Gradle module.

Open [Android-Lab.code-workspace](Android-Lab.code-workspace) for a focused view.
The [project map](docs/PROJECT_MAP.md) locates the Android builds/components,
Pokemon mechanics reference, logs, experiments, commands, and cleanup archive.

## Layout

```text
.codex/agents/       bounded model roles
android_lab/        Python implementation and installed lab entry point
config/             scenarios, routes and Docker definitions
tests/              unit and failure-path tests
tools/windows/      native SDK/AVD setup
tools/linux/        container startup scripts
docs/               maintained instructions, commands, state and project map
experiments/        dated findings and EXPERIMENT_LOG.md
knowledge_base/     summarized verified results, failures and assumptions
codex_memory/       compact machine-readable context for future Codex sessions
artifacts/          ignored runtime output
assets/             preserved local input assets/APKs
archive/            preserved recovery/reference material
```

## Install, run and verify

Install Python 3.11+ and uv, then run from the repository root:

```powershell
uv sync --extra test
uv run lab --help
uv run pytest -p no:cacheprovider
uv run python tools/verify_repository.py
uv build --out-dir artifacts/dist
```

The distribution remains `android-cloud-lab`; `lab` now loads
`android_lab.cli:main`. Configuration examples live in `config/`. Device/Proxmox
unit tests use mocks; passing them is not app compatibility or live deployment proof.

Use [START-HERE](START-HERE.md) for Windows setup, [commands](docs/COMMANDS.md)
for CLI and deployment operations, and [state](docs/STATE.md) for verified results.
The [Windows fleet guide](docs/FLEET.md) covers the new matrix-based create,
start, game-observation, and stop scripts.
Read [debugging](docs/DEBUGGING.md) and the [experiment log](experiments/EXPERIMENT_LOG.md)
before retrying an app failure. Model routing is in [MODEL_STRATEGY](docs/MODEL_STRATEGY.md).
Use [known failures](knowledge_base/known_failures.md) and
`codex_memory/attempted_approaches.json` to avoid repeating dead ends.

On Windows, isolate test output if Temp permissions interfere:

```powershell
New-Item -ItemType Directory -Force artifacts/tmp/tests | Out-Null
$env:TEMP=(Resolve-Path artifacts/tmp/tests).Path
$env:TMP=$env:TEMP
uv run pytest --basetemp artifacts/tmp/tests/pytest -p no:cacheprovider
```

SDK/AVD downloads under ignored `.tools/` and the development `.venv/` are local
inputs/tools, not tracked runtime reports. Existing downloads are preserved.
Logs, captures, reports, build output and new temporary test environments belong
under `artifacts/`. Never commit credentials, account data or APK downloads.
