# Windows fleet tests

September 14 status: the files are restored and host helper tests pass, but the
first create run exited 1 at its Matrix parameter default (`PSScriptRoot` was
empty). Fleet creation/start/game testing is unfinished. Work was paused for
repository cleanup; keep `artifacts/fleet-create-run.log` as the failed-run evidence.

Run from the repository root in PowerShell. The five scripts live in
`tools/windows/`; the shared helper is dot-sourced by the other scripts.
The device matrix is `config/fleet-matrix.json`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/New-FleetAvds.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Fleet.ps1 -MaxParallel 2
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Install-FleetGame.ps1 -ApkDir artifacts/pgo-apk
powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Stop-Fleet.ps1
```

`artifacts/pgo-apk` is this checkout's existing APK set. On another checkout,
supply a folder containing the official base APK and matching splits, or use
`-PullFromSerial emulator-5556` with the original API36 AVD running. Pulling copies
installed APK files; it does not transfer Google accounts or app data.

The default SDK/JDK and Android user directory are project-local under `.tools`.
Use `-SdkRoot`, `-JavaHome`, and `-AvdHome` to override them. API35 needs an official
system-image download if absent; API36/API37 were already installed here.
`-SkipInstall` skips downloads. Existing AVDs are preserved unless `-Force` is
explicitly supplied; the original named baseline AVDs are protected.

The matrix enables API35, fresh API36, and API37 renderer experiments on separate
ports 5562, 5564, and 5566. API33 is disabled. `-Only <name>` selects one enabled
entry. `MaxParallel` controls the number started in each batch; successful AVDs
remain running, so it is not a total memory/concurrency limit.

Startup records boot completion, AVD identity, properties, crash logs, Google
package evidence, and a PNG. A boot marker alone does not pass display readiness.
Failed AVDs are stopped by default; `-KeepOnFailure` retains them for diagnosis.
Game testing consumes only name-matched devices with `display_ok` in the startup
summary, installs/launches once, and records process/window/screenshot/crash
evidence. `process_running` is not confirmed foreground UI or successful login.
Authentication stays unverified until separately observed.

Logs and per-device results are in timestamped `artifacts/fleet-*` directories.
Latest summaries: `artifacts/fleet-latest.json` and
`artifacts/fleet-game-latest.json`. A failed startup/game result gives exit 1;
inspect the summaries because other devices may still have passed.

Run host checks with `Test-Fleet.ps1`, `Test-Profiles.ps1`, the full Python test
suite, and `tools/verify_repository.py`. Host tests do not prove guest compatibility.
Fresh runtime findings belong in `experiments/EXPERIMENT_LOG.md` and `docs/STATE.md`.

The original misplaced files and the pasted source were preserved under
`artifacts/fleet-input-20260914-180404/` before restoring the canonical paths.
