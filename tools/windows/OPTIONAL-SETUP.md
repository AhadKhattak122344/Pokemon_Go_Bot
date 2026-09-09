# Optional debug-image Magisk setup

Normal AVD startup and diagnostics do not install Magisk. Keep API 36 clean.
The supplied handoff already reports successful root on its separate API 34
baseline; do not repatch it as a response to a native translation crash.

`Install-Magisk.ps1` is an explicit temporary-runtime operation for the separate
API 34 x86_64 **debuggable Google APIs** AVD `baseline-rooted`. It checks API,
architecture, emulator/debug status, SELinux and these pinned upstream v30.7 files:

| Local file under `.tools/` | Upstream |
| --- | --- |
| `Magisk-v30.7.apk` | https://github.com/topjohnwu/Magisk/releases/download/v30.7/Magisk-v30.7.apk |
| `magisk-source/build.py` | https://raw.githubusercontent.com/topjohnwu/Magisk/v30.7/build.py |
| `magisk-source/scripts/live_setup.sh` | https://raw.githubusercontent.com/topjohnwu/Magisk/v30.7/scripts/live_setup.sh |

The Python helper checks SHA-256 before executing the upstream setup. The runtime
is temporary, lost on guest reboot, and is **not reapplied by ordinary startup**.
The command is only appropriate when deliberately preparing this owned debug image:

```powershell
uv sync --extra test
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Install-Magisk.ps1 -Serial emulator-5554
```

No installation or device-root transition was run during the repository migration.
Missing local files must be downloaded from the listed sources before this optional
operation. This is not a root-hiding, identity or integrity compatibility stack.
