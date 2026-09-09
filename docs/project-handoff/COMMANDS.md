# Current commands

Run from repository root unless noted. Full setup is in START-HERE.md.

```powershell
uv sync --extra test
uv run lab --help
uv run pytest -p no:cacheprovider
uv build --package android-cloud-lab
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Test-Profiles.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api36
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Test-Emulator.ps1 -Profile Api36
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Stop-Emulator.ps1 -Profile Api36
```

After loading the Android environment in the current process:

```powershell
uv run lab --config cloud-lab/config/api36.yaml status
uv run lab --config cloud-lab/config/api36.yaml diagnostics
uv run lab proxmox plan --config cloud-lab/config/proxmox.example.json
uv run lab proxmox --help
```

`proxmox preflight` and `deploy` use a configured real host and API token. `deploy`
requires a fresh `--out` journal. See the dedicated guide before invoking live writes.
