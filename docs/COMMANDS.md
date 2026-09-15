# Current commands

Run from repository root unless noted. Full setup is in START-HERE.md.

```powershell
uv sync --extra test
uv run lab --help
uv run pytest -p no:cacheprovider
uv build --out-dir artifacts/dist
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Test-Profiles.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api36
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Test-Emulator.ps1 -Profile Api36
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Stop-Emulator.ps1 -Profile Api36
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api361
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Test-Emulator.ps1 -Profile Api361
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Stop-Emulator.ps1 -Profile Api361
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api37
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Test-Emulator.ps1 -Profile Api37
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Stop-Emulator.ps1 -Profile Api37
```

After loading the Android environment in the current process:

```powershell
uv run lab --config config/api36.yaml status
uv run lab --config config/api36.yaml diagnostics
uv run lab --config config/pokemongo.yaml observe --package com.nianticlabs.pokemongo --duration 30 --interval 3
uv run lab --config config/pokemongo.yaml observe --package com.nianticlabs.pokemongo --duration 30 --interval 3 --launch
uv run lab --config config/pokemongo.yaml experiment --package com.nianticlabs.pokemongo
uv run lab --config config/pokemongo.yaml experiment --package com.nianticlabs.pokemongo --launch
uv run lab --config config/pokemongo.yaml experiment --login --login-timeout 180
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Run-Experiment.ps1 -Profile Api36 -Launch
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Run-Experiment.ps1 -Profile Api361 -Launch
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Run-Experiment.ps1 -Profile Api37 -Launch
uv run lab proxmox plan --config config/proxmox.example.json
uv run lab proxmox --help
uv run python tools/validate_against_history.py "use api 34 with magiskhide"
```

`lab observe` defaults to the configured app when `--package` is omitted and creates a fresh directory with `evidence.jsonl`, raw activity
snapshots, screenshots, and `observe.json`. It records capture completeness
separately from whether a requested package process was observed; neither result
establishes login, certification, or game progress. `--launch` starts only the
configured app component, and only after its pre-capture succeeds.

`Api361` is an isolated Android 16/API 36.1 test profile at `poke_api361_test`
on `emulator-5558`. It requires the exact official image
`system-images;android-36.1;google_apis_playstore;x86_64`; its lab YAML retains
`emulator.api: 36` because the YAML parser expects an integer SDK field.

`Api37` is an experimental Android 17/API 37 profile at `poke_api37_test` on
`emulator-5560`. It requires the separately installed official revision 6 or
newer `system-images;android-37.0;google_apis_playstore;x86_64` image; it is
intentionally not added to the default Bootstrap downloads. Revision 6 is the
minimum recommended by Google's emulator troubleshooting for Google
authentication/certification failures. API 36.1 remains known unstable. No game
success is claimed for API 37.

`Start-Emulator.ps1` accepts `-Gpu auto|host|software|lavapipe|swiftshader|swangle`
and `-DisableSharedSlots` for launch troubleshooting. A successful start reports
only boot/version checks; observe the display and app separately before treating
the emulator as ready.

`proxmox preflight` and `deploy` use a configured real host and API token. `deploy`
requires a fresh `--out` journal. See the dedicated guide before invoking live writes.

`tools/validate_against_history.py` checks a proposed approach against
`codex_memory/attempted_approaches.json`. A nonzero exit means the suggestion
matches a known non-retryable failure; read the printed source and use the listed
alternative or create a genuinely new bounded experiment.

# Proxmox deployment preparation

The maintained implementation is `android_lab/proxmox.py`, registered
as `lab proxmox`. Its unit tests use fake API responses. No real Proxmox host was
contacted during this change. Keep one host and one guest image as the pilot.

## Prepare a template on the intended host

1. Install Proxmox using its current official installer or the instructions for
   the exact Debian/PVE version. Do not run the old generic Ubuntu repository recipe.
2. Choose an Android guest image appropriate for the workload. Archived Bliss OS
   images are experiments, not a maintained or certified compatibility guarantee.
   Check the image's actual Android API and architecture; Bliss version numbers
   are not Android version numbers.
3. Upload the ISO through the Proxmox ISO-storage UI. Select actual disk storage,
   bridge, graphics and CPU options supported by the host. Start with 4 vCPU,
   8 GiB RAM and a 64 GiB disk as a pilot allocation, not a capacity benchmark.
4. Use a consistent BIOS/bootloader installation: OVMF with an EFI disk and UEFI
   installer, or SeaBIOS with the matching legacy bootloader. Include the optical
   drive in installation boot order; detach it and boot the installed disk afterward.
5. Validate cold boot, graphics, networking and authorized ADB. Enable the guest's
   debugging listener through its supported UI/console before `adb connect`.
   Keep ADB on an isolated management network or tunnel.
6. Test a disposable instance with the exact target APK and required native ABIs.
   Capture diagnostics and any legitimate app/backend integrity result separately.
   Root and a bridge property are not app acceptance tests.
7. Prepare an account-free template: do not clone signed-in Google sessions or
   test-account data. Shut it down cleanly and convert it to a Proxmox template.
   Record its VMID, image checksum, Android API and validation evidence.

The CLI deliberately supports a stopped, unlocked, single-NIC QEMU template on
one node, with ordinary sized virtual disks. Templates with passthrough/shared
host devices, hooks or custom topology require manual review. It does not create
an OS installation or generalize Android user data automatically.

## Configure and review offline

From the repository root:

```powershell
Copy-Item config/proxmox.example.json config/proxmox.json
uv run python -c "import uuid; print(uuid.uuid4())"
```

Edit `proxmox.json`: replace host/node/storage/bridge/template VMID, set a **fresh
namespace UUID** from the command above, and choose unused instance VMIDs/names.
The example points at a reserved example hostname and cannot deploy as-is.

```powershell
uv run lab proxmox plan --config config/proxmox.json --out artifacts/proxmox-plan.json
```

`plan` is offline, validates the configuration, and deterministically derives
locally administered MACs and SMBIOS UUIDs. These are VM inventory identities,
not Android IDs, IMEIs or certified handset identities. Run one deployment
process at a time; the API remains the authority for VMID allocation.

## Connect and preflight later

Set `PVE_TOKEN_ID` to `USER@REALM!TOKENID` and `PVE_TOKEN_SECRET` to its secret in the
process environment using your secret manager. Never put secrets in JSON or Git.
Use a trusted server certificate. For a private CA add `ca_file` to the config;
relative paths resolve beside that JSON file. TLS checks and redirect protection
remain enabled.

Give the user and privilege-separated token permission to inspect cluster VM
inventory, node status/network/storage and the source template. Deployment also
requires clone, VM allocation/configuration/power, datastore allocation and
bridge access permissions for the selected resources. Read preflight cannot
prove write permissions; inspect effective token ACLs in Proxmox before deploying.
See the [official token and privilege guide](https://github.com/proxmox/pve-docs/blob/master/pveum.adoc).

```powershell
uv run lab proxmox preflight --config config/proxmox.json --out artifacts/proxmox-preflight.json
```

Preflight rejects occupied IDs/names, unavailable templates/bridges/storage,
unsupported inherited settings, and insufficient RAM/disk plus configured reserves.
It counts all cloned virtual disks, including EFI/TPM state. This is a conservative
allocation check, not a performance or overcommit model. Missing visibility or
host changes can still make a later API write fail.

## Deploy only after pilot acceptance

```powershell
uv run lab proxmox deploy --config config/proxmox.json --out artifacts/proxmox-deploy.json
```

A fresh output path is required. The tool rechecks preflight, full-clones each VM,
waits for the clone UPID, configures the stopped VM, then starts it and waits for
the start UPID. Existing VLAN/firewall/MTU NIC options are preserved. It records
intent before writes and task IDs before waiting. Auto-start on host boot is off.
Success is `provisioned_android_unverified`: running QEMU is not booted Android.

On task failure, warning, timeout or uncertain network write, inspect the journal
and Proxmox task log before taking further action. There is no automatic delete,
adoption, retry, or rollback of a partially created VM. A timeout may leave an
operation running. Resolve it explicitly, then use a new output path and unused
VMIDs for any new deployment.

## Guest acceptance

With the actual guest debugging address in `adb.serial` of a local Android YAML
scenario, and ADB available in the current environment:

```powershell
uv run lab --config config/local-guest.yaml connect
uv run lab --config config/local-guest.yaml status
uv run lab --config config/local-guest.yaml diagnostics
```

Demonstrate cold-reboot persistence, a real ARM/ARM64 native test for each required
ABI, app install/launch/login and representative behavior, and isolated data for
two clones. Check Play Store certification in the UI; do not infer it from timestamps.
Only then benchmark concurrency, CPU, memory, graphics and storage at the intended
fleet size. Do not report unseen guest capabilities as passed.

Protocol sources and the rejected handoff claims are recorded in
[DEBUGGING.md](DEBUGGING.md).

# Explicit emulator debug-root controls

From the root after loading the Android environment:

```powershell
uv run lab root status
uv run lab root enable
uv run lab root disable
uv run lab root self-test
```

Set `LAB_SERIAL` or select a YAML scenario for the intended owned debug emulator.
`status` only probes; it does not run `su`. Enable/disable uses `adb root`/`adb unroot`,
waits for reconnect and verifies numeric UID. Self-test restores the original ADB
privilege in a finally block. Each action writes a JSON report. Unsupported builds
and physical devices are rejected before changes. Do not run transitions concurrently.

ADB daemon privilege is distinct from app-level Magisk `su`. Optional unavailable
probes are reported as unknown. Nothing here patches boot images or hides root.
The separately available [Windows Magisk setup](../tools/windows/OPTIONAL-SETUP.md)
is only for the owned API 34 debug image and requires explicit invocation.

The supplied handoff already reports root on the modified `baseline` AVD; do not
repatch it to fix ARM translation SIGILL. Keep `poke_api36_test` clean until its
ordinary authentication failure is understood. Historical live-root reports from
earlier sessions are not current migration verification evidence.

## CLI configuration and optional Linux runtime

Global `--config YAML` precedes the Android command; Proxmox JSON `--config`
follows `proxmox plan/preflight/deploy`. `LAB_SERIAL`, `ADB_SERVER_SOCKET`,
`LAB_ARTIFACTS` and `LAB_PROFILE` override the corresponding scenario values.
The default scenario is API 34 for Docker; choose `config/api36.yaml` for native
API 36. Set the real app package/activity before install/smoke tests. `smoke`
clears logcat; capture diagnostics first when preserving an existing failure.

Linux requires Docker Engine/Compose v2 and working `/dev/kvm` on an x86_64 host.
The container is Google APIs API 34 and does not include Play Store. Do not repeat
the reported software-emulated Windows/WSL failure without new KVM evidence.
Run from the repository root:

```sh
docker compose -f config/docker/docker-compose.yml -f config/docker/docker-compose.kvm.yml build
LAB_PROFILE=nested-virt uv run lab up
uv run lab status
uv run lab install --apk assets/apks/your-app.apk
uv run lab smoke
LAB_PROFILE=nested-virt uv run lab down
uv run lab location set --lat 40.758 --lon -73.985
uv run lab location follow --gpx config/routes/sample_city_walk.gpx --speed-mps 1.4
```

Location calls are emulator QA inputs, not proof an app consumed them. Container
startup retains its bounded two-attempt boot policy. Docker lifecycle commands
require this source checkout; device and Proxmox commands also work from a wheel.

## Login observation

`lab --config config/pokemongo.yaml experiment --login --login-timeout 60`
launches and observes. It does not select a Google account. If an account picker
appears, choose the intended account manually. Classifications are evidence hints;
confirm a Unity dialog or game map visually. A timeout leaves authentication
unverified. Preserve the JSON report even when boot or capture fails.
