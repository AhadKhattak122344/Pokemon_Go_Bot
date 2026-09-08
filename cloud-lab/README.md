# Optional Linux Android emulator harness

This harness provides container, ADB, and deterministic route utilities for
user-supplied APKs. It is not a fleet-provisioning or device-identity system.

**Validation:** Python unit tests pass and the launch checker ran against the local
Windows emulator. Docker is absent on the development machine, so Docker image build
and Linux emulator boot remain unverified.

Use a Linux **x86_64** Ubuntu 22.04/24.04 host with Docker Engine, Docker Compose v2,
GNU Make, at least 4 vCPU, 8 GB RAM, and approximately 20 GB free SSD space.
The emulator uses the official **Android 14 / API 34 Google APIs x86_64** image.
ARM cloud hosts are not supported by this harness.

```sh
cd cloud-lab
make build
make up
make smoke
make down
```

The default profile uses software rendering and `-accel off`. Expect slow boot and
inference on ordinary cloud VMs. When the host actually exposes working `/dev/kvm`:

```sh
make PROFILE=nested-virt up
make PROFILE=nested-virt smoke
make PROFILE=nested-virt down
```

The emulator starts without a bundled application. Install a user-supplied APK with
the CLI after boot. A failed cold boot is retried once. SIGTERM stops owned
emulator/relay processes. No privileged container or Docker socket mount is required.

Ports 5037 (ADB server) and 5555 (guest ADB relay) bind to host loopback only.
The Python container talks to the internal ADB server and uses the exact platform-tools
binary copied from the SDK build stage. Do not expose these ports to the internet.
Use an SSH tunnel for access from another machine.

Optional Python CLI on the host (`python3.11+`, platform-tools on PATH):

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
lab up
lab status
lab install --apk apks/your-app.apk
lab smoke
lab down
```

Set `LAB_PROFILE=nested-virt` for the CLI's KVM profile. Configuration defaults to
`config/default.yaml`; `--config` accepts another file. Configure your package,
launcher activity, and optional expected ready activity when testing a different app.
`ADB_SERVER_SOCKET`, `LAB_SERIAL`, and `LAB_ARTIFACTS` override connection/output values.

The smoke test launches only the configured app, waits for its ready activity, checks
the crash buffer, and writes a screenshot, logcat, dumpsys location, metadata, and JUnit
XML under a unique `artifacts/` run directory. A failed check exits nonzero. This is
an app-launch test, not a GPS-consumption or game-operation test.

For location-aware apps you control, optional deterministic emulator GPS utilities:

```sh
lab location set --lat 40.758 --lon -73.985
lab location follow --gpx config/routes/sample_city_walk.gpx --speed-mps 1.4
```

These use the emulator's `geo fix` API, validate coordinates, interpolate a finite
route at the selected speed, and write a CSV trace. They do not include a companion
mock-provider APK or claim that an arbitrary app consumed the fix.

## Build reproducibility and scope

Command-line-tools build 11076708 and direct Python dependencies are pinned. SDK
manager's emulator, platform-tools, Android 14 image revisions, and OS package updates may change upstream;
archive built image digests for reproducible CI. This is not a fully immutable SDK lock.

The reference notes describe components that are not supplied by this repository.
noVNC, infrastructure provisioning, managed PaaS integration, identity spoofing,
attestation bypasses, and external backend automation are not implemented.

Official references: [emulator architecture and acceleration](https://developer.android.com/studio/run/emulator-acceleration),
[emulator CLI](https://developer.android.com/studio/run/emulator-commandline),
[SDK manager](https://developer.android.com/tools/sdkmanager).

For explicit emulator debug-root operations and a review of the root-management
reference code, see [ROOT-CONTROLS.md](docs/ROOT-CONTROLS.md).
