# Android QA Lab

Windows-native Android emulator tooling and a Python QA CLI for user-supplied APKs,
with an optional Linux Docker harness and Proxmox template-clone workflow.
The repository contains no active Android application or buildable app module.

## Layout

- `cloud-lab/orchestrator/`: installed `lab` CLI, ADB, health, diagnostics, smoke tests, debug-root controls, Proxmox client.
- `cloud-lab/config/`: Android scenarios, route fixtures, Proxmox example configuration.
- `cloud-lab/tests/`: mocked unit and failure-path tests.
- `cloud-lab/scripts/`, Dockerfiles and Compose files: optional Linux runtime.
- `tools/windows/`: repo-local SDK setup and native AVD management.
- `docs/project-handoff/`: current evidence, constraints and next steps.
- `docs/PROXMOX-VM-PREP.md`: future Proxmox deployment procedure.
- `assets/`: ignored local downloads; the historical manifest records checksums, not compatibility.
- `archive/`: deduplicated flat export, recovery provenance and superseded proposals. Never part of the build or Docker context.

## Install and verify

Install Python 3.11+ and uv. From the repository root:

```powershell
uv sync --extra test
uv run lab --help
uv run pytest -p no:cacheprovider
```

The root uv workspace installs `android-cloud-lab` from `cloud-lab/` as an editable
package. There is one CLI implementation, `orchestrator.cli:main`. No external
server, device, Docker daemon or Google account is needed for unit tests.

On Windows, when Temp permissions interfere with pytest:

```powershell
New-Item -ItemType Directory -Force .tmp/tests | Out-Null
$env:TEMP=(Resolve-Path .tmp/tests).Path
$env:TMP=$env:TEMP
uv run pytest --basetemp .tmp/tests/pytest -p no:cacheprovider
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Test-Profiles.ps1
```

## Run on Windows

Use [START-HERE.md](START-HERE.md) for the clean API 36 workflow. The profiles are:

| Profile | AVD | Serial | Purpose |
| --- | --- | --- | --- |
| `Api36` (default) | `poke_api36_test` | `emulator-5556` | Clean Android 16 compatibility baseline |
| `Play` | `baseline` | `emulator-5554` | Existing API 34 Google Play image; supplied handoff reports it was rooted externally |
| `Rooted` | `baseline-rooted` | `emulator-5554` | Separate API 34 Google APIs debug image |

Startup never installs Magisk or patches an image. The two API 34 profiles share
port 5554 and cannot run together. Stop/test operations check the AVD name before
targeting a port. The API 36 profile remains independent.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api36
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Test-Emulator.ps1 -Profile Api36
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Stop-Emulator.ps1 -Profile Api36
```

Before ADB CLI commands, load `tools/windows/Android-Environment.ps1` into the
current shell as shown in START-HERE. Supply an APK you own or are authorized to
test; edit a scenario's package/activity before running `lab smoke`. Diagnostic
capture does not launch apps, clear logcat, attempt sign-in, or change root state.
Artifacts can contain app/account data; they remain ignored by Git.

## Proxmox and Linux

```powershell
uv run lab proxmox plan --config cloud-lab/config/proxmox.example.json
```

This is an offline plan. Live `preflight` only reads; `deploy` full-clones an
already-installed, stopped template, configures each clone and waits for start.
See [Proxmox preparation](docs/PROXMOX-VM-PREP.md) for configuration, credentials,
permission checks, task recovery and guest acceptance. It is not a web API, job
queue, image installer, or proof of target-app acceptance.

Linux Docker commands and prerequisites are in [cloud-lab/README.md](cloud-lab/README.md).
Do not repeat the software-emulated Docker experiment on the Windows/WSL host
from the supplied handoff; it lacked `/dev/kvm`. Native WHPX is the local path.

## Build and limitations

There is no Android build target: commit `cbc1d35` removed the reconstructed app.
The remaining flattened files have misleading extensions (some Gradle filenames
are WebP images). They are preserved under `archive/recovered/`, not silently
turned into a new app. Build the Python distribution with `uv build --package
android-cloud-lab`.

API 34 ARM translation SIGILL and API 36 sign-in failure are **reported historical
observations**, not bugs proven fixed by the current unit tests. Proxmox live
operation, Linux/KVM boot, certification and third-party authentication require
real environment tests. See [current state](docs/project-handoff/CURRENT_STATE.md).

## Troubleshooting

- Missing ADB: bootstrap the SDK and load the Android environment, or set `adb.executable` in your YAML scenario.
- Missing Docker: use the native Windows scripts, or install Docker/Compose on the intended Linux host.
- Unauthorized device: select the exact serial and approve debugging inside Android.
- Proxmox TLS error: configure the trusted CA; certificate verification is never disabled.
- Existing VMID or timed-out task: inspect the journal and Proxmox task log before retrying. Existing VMs are never overwritten.
- Invalid config: use the committed examples; YAML `on`/`off` values must be quoted.
