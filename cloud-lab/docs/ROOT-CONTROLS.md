# Emulator root controls and review of the supplied implementation

The working implementation is `orchestrator/root.py`, exposed through `lab root`.
The Windows Android 14 profile is started and verified with
`../../tools/Start-Emulator.ps1` and `../../tools/Test-Emulator.ps1`.

## Commands

From the workspace root on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File tools/Start-Emulator.ps1 -Profile Rooted
powershell -ExecutionPolicy Bypass -File tools/Test-Emulator.ps1 -Profile Rooted
```

With the Python package installed, from `cloud-lab/`:

```sh
lab root status
lab root enable
lab root disable
lab root self-test
```

`status` performs read-only probes. `enable` and `disable` explicitly switch the
selected emulator's ADB daemon privilege using `adb root` and `adb unroot`, wait for
reconnection, and verify the resulting numeric UID. Unsupported builds and physical
devices are rejected before a privilege change. Each CLI invocation writes a unique
JSON report, including failures. Existing files are overwritten only if an explicit
`--out` path is supplied.

The self-test exercises both modes and restores the original mode in a `finally`
block. A restoration failure is surfaced. Do not run root transitions concurrently
with another test runner: restarting adbd temporarily interrupts ADB connections.

This controls the **ADB daemon**, not the app's UID. It does not grant every app
superuser privileges or install a superuser prompt/permission manager. Module listings
are observations of an accessible directory, not proof that modules are active.
An unavailable probe is reported as unknown, not as a successful negative result.

## Verification on the current emulator

On Android 14 / API 34 x86_64, `userdebug`, live verification observed:

| Stage | ADB UID | SELinux |
| --- | --- | --- |
| Original | 2000 (shell) | Enforcing |
| Root enabled | 0 (root) | Enforcing |
| Root disabled | 2000 (shell) | Enforcing |
| Restored | 2000 (shell) | Enforcing |

The Python suite passed 18 tests, including failures, reconnects, idempotency, and
restoration. The live JSON report is under the workspace `artifacts/root-self-test-*.json`.
At the initial debug-root verification, no Magisk executable was found in PATH.

## Magisk installation (2026-09-08)

The separate `tools/Install-Magisk.ps1` wrapper applies the official Magisk
v30.7 temporary AVD setup to the project's API 34 x86_64 emulator. It validates the
downloaded APK and upstream `build.py` / `live_setup.sh` hashes before execution,
checks emulator capabilities, enables ADB root, and invokes upstream `setup_avd()`.
The required local downloads are under `.tools/`; this is not a download bootstrap.

Live verification observed the daemon reporting `30.7:MAGISK:R`, its runtime at
`/debug_ramdisk`, Android boot completed, and SELinux `Enforcing`. The management
app displayed installed version `30.7 (30700)` for both core and app. Evidence:
`artifacts/verification/magisk.png` and `magisk-window.xml`.

This setup briefly restarts Android's app processes. Its runtime is lost after an
emulator reboot; re-run the wrapper to restore it. It does not patch the boot image.
The upstream script emits missing `magisk32` copy warnings because this guest exposes
only the 64-bit runtime; the primary x86_64 binary and daemon were verified afterward.

## Problems in the supplied code

1. `install_magisk` calls `su` to install the framework that is supposed to provide
   `su`. Installing a Magisk APK installs its management application; initial root
   setup is a separate boot/init_boot/recovery-image operation.
2. Directly remounting `/system` and appending to `build.prop` is not a systemless
   overlay. The code supplies no image-specific rollback or verification.
3. Replacing `su` with a bind mount of a shell can interfere with later calls to
   `su`; calling this operation successful without checking its exit code hides errors.
4. Disabling `com.android.shell` risks breaking the ADB control path that the rest
   of the system relies on.
5. A module directory or process name does not establish that a module is compatible,
   active, or providing a particular security property.
6. Several installers and settings are assumed rather than validated against specific
   module versions. Downloaded responses are not checked for success or integrity.
7. The persistence code manually executes module boot scripts outside their normal
   lifecycle and suppresses failures. It does not provide reliable recovery.
8. A local build-property string is not a cryptographically verified device-integrity
   verdict. This implementation makes no claims about passing attestation.

## Scope

Implemented: emulator capability detection, selected-device root toggles, reconnect
handling, privilege verification, read-only observations, JSON reports, and restoration
tests. Existing app launch/model tests remain available.

Not implemented by the debug-root controls: Magisk or custom-kernel installation, Zygisk/Shamiko/SUSFS integration,
boot persistence scripts, root concealment, attestation spoofing, OCR, or runtime
injection into other applications. The supplied snippets are not installed or executed
as a complete stack. Any image modification would require a separate, reproducible
image-specific design and rollback plan; these controls operate on the working emulator.
Magisk's temporary installation is provided separately as described above.

## Primary references

- [Magisk emulator FAQ](https://topjohnwu.github.io/Magisk/faq.html):
  the supported temporary AVD runtime setup and its reboot limitation.

- [Android virtual-device documentation](https://developer.android.com/studio/run/managing-avds):
  emulator image selection and `adb root` / `adb unroot`. Google Play Store release
  images do not offer this debug-root path.
- [Magisk installation documentation](https://topjohnwu.github.io/Magisk/install.html):
  initial installation depends on the appropriate device boot/init_boot/recovery image.
- [Play Integrity overview](https://developer.android.com/google/play/integrity/overview):
  integrity assessment is a separate API and backend-verification workflow.
