# Build and test the original Android app

The working Android project is in **recovered/**. The loose files in the workspace
root are the original damaged export and should not be opened as an Android project.

**Built APK:** `artifacts/RegiBot-debug.apk` (debug signed; for local testing).

From PowerShell in this workspace:

```powershell
# Build the APK, run unit tests, and run Android lint.
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Build-App.ps1

# Open the emulator window, install the APK, and launch RegiBot.
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Start-Emulator.ps1

# Exercise all five models on the running emulator.
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Test-App.ps1

# Shut down the emulator.
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Stop-Emulator.ps1
```

The workspace already has a portable JDK and Android SDK under `.tools/`.
For a fresh checkout or machine, first run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Bootstrap-Android.ps1 -WithEmulator
```

Bootstrap downloads a checksum-verified Temurin JDK 17, Android command-line tools,
build packages, and the optional emulator image. It accepts the SDK licenses for
this toolchain. It does not change the machine's persistent PATH or JAVA_HOME.
Downloads need internet access and several GB of free disk space.

The tested device is **Android 11 / API 30 / x86**, running under Windows WHPX.
Keep this ABI: MediaPipe 0.10.14 contains x86, ARMv7, and ARM64 JNI libraries, but
no x86_64 library. Compile SDK 35 is independent of the emulator's Android version;
the app's minimum SDK remains 30 and target remains 34.

Tests cover APK installation, launch through to the home screen, and real inference
through all five bundled models. They do not test game-server behavior or any
third-party game interaction. Accessibility and overlay permissions are not enabled
automatically by the test harness; they can be reviewed in the app's Permissions screen.

The separate **cloud-lab/** directory contains a Linux Docker emulator harness based
on the reference files. Its Python tests pass, but the Docker images have not been
built or booted here because Docker is not installed. Start with the verified Windows
path above. See `cloud-lab/README.md` for the cloud commands and limitations.

See `recovered/README.md` for recovery provenance and validation details.

Emulator debug-root controls are available through `tools/Root-Emulator.ps1`
(`status`, `enable`, `disable`, `self-test`). See
`cloud-lab/docs/ROOT-CONTROLS.md` for commands, scope, and the live verification results.

Magisk 30.7 is installed on the current emulator using the official temporary AVD
setup. After an emulator reboot, reapply its runtime with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Install-Magisk.ps1
```

This uses the checksum-pinned APK and upstream scripts already downloaded under
`.tools/`; those files must be present. It briefly restarts Android app processes.
The Magisk app remains installed across reboots, but its runtime is temporary.
See `artifacts/verification/magisk.png` for the verified installed-version screen.

Fresh checkouts: see tools/OPTIONAL-SETUP.md for Python and Magisk downloads.
