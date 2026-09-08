# Optional Windows Python and Magisk setup

The Android build and device tests do not require Python or Magisk.
For the optional cloud CLI and root controls, install Python 3.11 or newer,
then run from the repository root:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e './cloud-lab[test]'
```

The PowerShell wrappers use the existing portable `.tools/python/python.exe`
when present, otherwise `.venv/Scripts/python.exe`.

For optional Magisk setup, download the following upstream v30.7 files into
these paths (create the directories first):

| Local path | Download |
| --- | --- |
| `.tools/Magisk-v30.7.apk` | https://github.com/topjohnwu/Magisk/releases/download/v30.7/Magisk-v30.7.apk |
| `.tools/magisk-source/build.py` | https://raw.githubusercontent.com/topjohnwu/Magisk/v30.7/build.py |
| `.tools/magisk-source/scripts/live_setup.sh` | https://raw.githubusercontent.com/topjohnwu/Magisk/v30.7/scripts/live_setup.sh |

`tools/install_magisk.py` verifies the SHA-256 of all three files before use.
Run `tools/Install-Magisk.ps1` only after starting the project's API 30 x86
emulator. The installation is temporary and must be reapplied after reboot.
Downloaded tools and local emulator state are intentionally not committed.
