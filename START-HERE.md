# Start here

Run these commands from the repository root in PowerShell. Install Python 3.11+
and uv first.

```powershell
uv sync --extra test
uv run lab --help
uv run pytest -p no:cacheprovider
```

Prepare the repo-local SDK only if needed. Bootstrap accepts the Android SDK
licenses and downloads the selected platform tools/images. Existing AVDs are not
recreated by startup. Do not replace the known rooted API 34 image to investigate
an unrelated crash.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Bootstrap-Android.ps1 -WithEmulator
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api36
```

Load ADB into the **current** PowerShell process, then inspect the clean API 36 AVD:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. ./tools/windows/Android-Environment.ps1
uv run lab --config cloud-lab/config/api36.yaml status
uv run lab --config cloud-lab/config/api36.yaml diagnostics
```

Each capture gets a new directory under `artifacts/`. To investigate an authorized
app's sign-in failure, reproduce it manually once, then collect diagnostics with
`--package com.example.app` replaced by its real package. No account switching,
root installation or automated sign-in is performed.

For your own test APK, copy `cloud-lab/config/api36.yaml` to a local YAML file and
set its real `app.package`, `app.activity`, and optional `ready_activity`:

```powershell
uv run lab --config cloud-lab/config/api36.yaml install --apk C:/path/to/your-app.apk
uv run lab --config cloud-lab/config/local-app.yaml smoke
```

The example package is a configuration placeholder, not a supplied app. `smoke`
clears logcat for its launch check; use `diagnostics` first when preserving a
pre-existing failure. Stop the selected AVD when finished:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Stop-Emulator.ps1 -Profile Api36
```

To prepare Proxmox without a host:

```powershell
uv run lab proxmox plan --config cloud-lab/config/proxmox.example.json
```

Continue with [the deployment guide](docs/PROXMOX-VM-PREP.md) when a host is available.
For Windows Temp errors and the full layout, see [README.md](README.md).
