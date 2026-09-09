# Python Android QA component

This component supplies the single installed `lab` CLI. Prefer the root uv
workspace commands in [../START-HERE.md](../START-HERE.md); `uv sync --extra test`
and `uv run lab --help` also work from this directory.

## CLI

`up`, `down` manage the optional Linux Docker emulator. `status` checks selected
ADB transport, Android boot and package-manager readiness. `connect` connects a
configured TCP serial and verifies authorization. `install --apk FILE` installs a
user-supplied APK. `smoke` launches the configured component and saves evidence.
`diagnostics` saves read-only device state/logs/screenshots without clearing logs.
`root {status,enable,disable,self-test}` controls debug ADB privileges explicitly.
`location {set,follow}` uses emulator geo controls for apps you are authorized to test.
`proxmox {plan,preflight,deploy}` manages the prepared-template workflow.

Global `--config YAML` precedes the command. Proxmox has its own JSON `--config`
after the command. Defaults are `config/default.yaml` in a source checkout or its
packaged counterpart in an installed wheel. These copies are compared by tests.
`LAB_SERIAL`, `ADB_SERVER_SOCKET`, and `LAB_ARTIFACTS` override connection/output
values; `LAB_PROFILE` selects the Docker accelerator profile. Values are validated.
For API 36 use `--config config/api36.yaml`; the default API 34 config is retained
for the Linux image. Package/activity fields must describe your real test app.

Diagnostics can contain account data and remain in ignored artifact directories.
A smoke test clears logcat, launches the configured activity and checks foreground
state/crash evidence; it is not a sign-in test. Collect diagnostics first when
preserving an existing failure. APKs, account credentials, web APIs, databases and
job queues are not bundled.

## Optional Linux runtime

Use a Linux x86_64 host with Docker Engine/Compose v2, at least 4 vCPU, 8 GiB RAM,
SSD storage and real `/dev/kvm` access. Windows-native AVDs are the local path.
Do not rerun the handoff's known software-emulated Windows/WSL experiment.

From `cloud-lab/` on the intended Linux host:

```sh
make build
make PROFILE=nested-virt up
uv run lab status
uv run lab install --apk apks/your-app.apk
uv run lab smoke
make PROFILE=nested-virt down
```

Configure the app before `smoke`. The image is Google APIs Android 14/API 34
x86_64 and does not bundle Play Store. The KVM override mounts `/dev/kvm`.
The retained `cheap-cloud` software-emulation profile is explicitly slow and does
not acquire acceleration by installing Docker. No local Docker boot was repeated
in this migration.

Compose binds ADB ports to loopback. The internal daemon starts with
`adb -a -P 5037 start-server`. Container startup owns two bounded cold-boot attempts;
the CLI waits for their combined health window. It does not add another retry loop.
Container `COPY` paths are relative to the root build context and exclude `archive/`.

```sh
uv run lab location set --lat 40.758 --lon -73.985
uv run lab location follow --gpx config/routes/sample_city_walk.gpx --speed-mps 1.4
```

These APIs do not prove an arbitrary app consumed a location fix. Root controls
are documented in [docs/ROOT-CONTROLS.md](docs/ROOT-CONTROLS.md). Proxmox operation
is documented in [../docs/PROXMOX-VM-PREP.md](../docs/PROXMOX-VM-PREP.md).

## Build and test

From the repository root:

```sh
uv sync --extra test
uv run pytest -p no:cacheprovider
uv build --package android-cloud-lab
```

The wheel contains `orchestrator` and its default scenario. Docker lifecycle
commands require a source checkout containing Compose files; device and Proxmox
commands work from the installed wheel. All external unit-test dependencies are
mocked. Docker image build and live guest/Proxmox checks are separate integration
work, never inferred from this test suite.
