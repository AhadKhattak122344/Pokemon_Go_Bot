# Android 14 emulator setup

## Install the toolchain

From PowerShell in the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Bootstrap-Android.ps1 -WithEmulator
```

Bootstrap downloads a checksum-verified Temurin JDK 17, Android command-line tools,
platform tools, the Android emulator, and two Android 14 x86_64 images. It accepts
the Android SDK licenses for this local toolchain and does not change the machine's
persistent `PATH` or `JAVA_HOME`.

## Google Play profile

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Start-Emulator.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Test-Emulator.ps1
```

This starts `baseline` on port 5554 with the Android 14 Google Play image. The live
test verifies boot completion, API 34, x86_64, Google Play services, the Play Store,
and the expected non-rooted ADB state. Sign in through the emulator UI before
installing apps tied to a Google account.

## Rooted profile

Stop the Play profile before starting the rooted one:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Stop-Emulator.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Start-Emulator.ps1 -Profile Rooted
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Test-Emulator.ps1 -Profile Rooted
```

This starts `baseline-rooted` on port 5554 using the Android 14 Google APIs image.
The startup enables ADB root, applies the checksum-pinned Magisk 30.7 temporary AVD
runtime, and installs the Magisk manager. The live test verifies UID 0, Magisk, Play
services, API level, ABI, and boot state. See `tools/OPTIONAL-SETUP.md` for the three
upstream Magisk files required by a fresh checkout.

The Magisk runtime is temporary and is reapplied by the start script after a reboot.
The rooted profile does not include the Google Play Store image. Google documents
that Play Store images cannot use ADB root, so the two profiles serve different test
purposes.

## Install and launch your own APK

```powershell
. tools/Android-Environment.ps1
& "$env:ANDROID_HOME/platform-tools/adb.exe" -s emulator-5554 install -r C:\path\to\app.apk
```

Use the app's real package and activity with `adb shell am start` when you want to
launch it. The repository intentionally includes no application APK, source, models,
account credentials, identity-spoofing configuration, or integrity-bypass modules.

## Stop the emulator

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Stop-Emulator.ps1
```

The stop script waits until port 5554 is released so the other profile can start
without a race.
