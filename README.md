# Android 14 Emulator Lab

Reproducible Android Studio/QEMU emulator tooling for Windows, plus an optional
Linux Docker QA harness. The repository does not contain an Android application.

## Windows quick start

```powershell
git clone https://github.com/AhadKhattak122344/Pokemon_Go_Bot.git
cd Pokemon_Go_Bot
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Bootstrap-Android.ps1 -WithEmulator
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Start-Emulator.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Test-Emulator.ps1
```

The default profile is:

- Android version: Android 14 / API 34
- Emulator: Android Studio QEMU emulator
- System image: Google Play, x86_64
- AVD name: `baseline`
- ADB serial and port: `emulator-5554` / 5554
- Hardware profile: Pixel 7, 4 cores, 4 GB RAM, automatic GPU acceleration
- Startup: Quick Boot snapshots after the first cold boot

This profile includes Google Play services and the Play Store. Sign in inside the
emulator to install account-bound apps such as Google Drive.

## Rooted test profile

Google Play system images are release-signed and do not permit ADB root. A separate
Android 14 Google APIs AVD named `baseline-rooted` provides ADB root and a temporary
Magisk 30.7 runtime:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Start-Emulator.ps1 -Profile Rooted
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Test-Emulator.ps1 -Profile Rooted
```

Run only one profile at a time because both use port 5554. Magisk is reapplied when
the rooted profile starts. This repository does not include root concealment,
fingerprint spoofing, identity rotation, or Play Integrity/SafetyNet bypasses.

Pokémon GO officially does not support rooted devices and may also reject emulator
environments. The Play profile supplies the supported Google components, but app
availability and acceptance remain controlled by Google Play and the app developer.

See [START-HERE.md](START-HERE.md) for commands and
[cloud-lab/README.md](cloud-lab/README.md) for the optional Linux harness.
