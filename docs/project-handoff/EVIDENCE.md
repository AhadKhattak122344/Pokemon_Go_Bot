# Verification evidence

Session: September 9, 2026, Windows checkout on `main`.

## Before restructuring

- Inspected Git status, current branch, ten-entry history request and full tracked
  inventory. History contains two commits, ending at `cbc1d35`. `git fetch origin`
  succeeded with network-enabled execution; `origin/main` also resolved to `cbc1d35`.
- Preserved initial tracked/untracked working files and both Git diffs in a sibling
  `_backups/pre-handoff-20260909-095419/` recovery snapshot. Caches were excluded.
- Read supplied `Project_Handoff.docx`, repository docs, active Python/PowerShell/
  Docker code and recovery metadata. The handoff was present, not invented.
- `uv sync --extra test` succeeded from `cloud-lab/` after allowing dependency downloads.
- Functional baseline: **72 pytest tests passed**, plus **20 Proxmox unittest cases**;
  Windows profile, wrong-AVD and syntax checks passed. No folder reorganization
  preceded that baseline.

## After restructuring

- Root `uv sync --extra test` succeeded; frozen sync also succeeded.
- Root `uv run pytest --basetemp .tmp/final-tests/pytest -p no:cacheprovider`:
  **92 passed** using Python 3.12.10 and pytest 8.3.5.
- `uv run lab --help`, `lab proxmox --help`, `lab diagnostics --help` succeeded.
  Python inspection resolved the entry point to `cloud-lab/orchestrator/cli.py`.
- `uv run lab proxmox plan --config cloud-lab/config/proxmox.example.json` returned
  `planned_offline` and `android_readiness: unverified` without host access.
- `uv build --package android-cloud-lab` produced the source archive and wheel.
- Installed that wheel in a separate virtual environment: `lab --help` passed,
  `orchestrator.cli` resolved inside its `site-packages`, and the packaged default
  configuration loaded correctly without depending on the source config directory.
- PowerShell profile/syntax tests and Bash `-n` checks for both Linux scripts passed.
- Docker Compose merged base/KVM configuration parsed successfully; no daemon boot,
  emulator build, container launch or KVM test was performed.
- All **280** original flat-export paths resolve to retained bytes matching their
  SHA-256 values. **139** byte-identical duplicates were removed; differing variants
  remain. No build/runtime imports reference the archive.
- Exported all staged files into a clean tree with no Git metadata, SDK, prior
  virtual environment or runtime artifacts. `uv sync --offline --frozen --extra
  test` created a fresh environment from the pinned dependency cache. The exported
  tree passed **92 tests**, all **280 archive hashes**, **20 active documentation
  files**, **13 CLI help paths**, and the PowerShell profile/syntax checks.
- The clean-export hash gate caught pre-existing Git index newline normalization.
  Re-staging archive bytes under explicit preservation attributes corrected it;
  hashes then matched in both the Git index and fresh export.
- The moved PowerShell process wrapper successfully invoked ADB `version` outside
  the sandbox (platform-tools 37.0.1). Sandbox-only Windows preference-directory
  resolution failed; no image or AVD was changed to work around it.
- Both `git diff --check` and `git diff --cached --check` passed. Tracked-file
  inspection found no caches, environments, runtime artifacts or build outputs.

## Android build qualification

There is no active Android app module. Git commit `cbc1d35` deliberately removed
it; the recovered settings still include missing `:app`. The root's supposed
Gradle wrapper/settings are actually image payloads from a scrambled export.
An exploratory `recovered/gradlew.bat ... tasks --offline --no-daemon` attempt
before migration failed while the legacy wrapper tried to download Gradle through
the restricted network. It is **not a passing Android build**. This skeleton is
now reference-only, and no app source was fabricated to manufacture a green result.

## External limitations

No real Proxmox server, target-app login, Android boot, root transition, or integrity
test was exercised in this migration. API 34 SIGILL/API 36 sign-in findings are
attributed to the supplied handoff, not to current tests. Mocked success does not
establish those external outcomes.
