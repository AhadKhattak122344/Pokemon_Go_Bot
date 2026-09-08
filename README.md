# Pokemon Go Bot / RegiBot

Restored Android source, bundled TensorFlow Lite models, Windows build and emulator
scripts, and an optional Linux Docker test harness.

## Quick start (Windows)

Install Git, then clone this repository and run these commands in PowerShell:

```powershell
git clone https://github.com/AhadKhattak122344/Pokemon_Go_Bot.git
cd Pokemon_Go_Bot
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Bootstrap-Android.ps1 -WithEmulator
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Build-App.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Start-Emulator.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Test-App.ps1
```

**Alternative: Deploy Docker Emulator Directly**

If you have Docker Desktop installed and want to skip the full build setup:

```powershell
cd Pokemon_Go_Bot\cloud-lab
docker compose build
docker compose up -d --wait --wait-timeout 1900 emulator
docker compose run --rm lab smoke
docker compose down
```

See [cloud-lab/WINDOWS_DEPLOYMENT.md](cloud-lab/WINDOWS_DEPLOYMENT.md) for complete step-by-step Windows instructions with troubleshooting.

Bootstrap downloads JDK 17 and the Android SDK and accepts SDK licenses. Allow
several GB of disk space and internet access for SDK and Gradle dependencies.
The build creates `artifacts/RegiBot-debug.apk` and runs JVM tests and Android lint.
Emulator testing uses Android 11 / API 30 / x86; Windows WHPX acceleration must be
available. You can also open `recovered/` in Android Studio.

## Repository contents

- `recovered/`: working Android project, Gradle wrapper, resources, all five real
  model binaries, tests, and recovery provenance.
- `tools/`: build, setup, recovery, and emulator utilities.
- `cloud-lab/`: optional Python CLI and Linux Docker emulator harness.
- `START-HERE.md`: detailed Windows commands and runtime limitations.
- Loose files in the root: original damaged export, preserved for recovery history.
  These are not the working Android project.

SDKs, JDKs, Python environments, emulator disk images, credentials, caches, and
compiled outputs are excluded. Build dependencies are downloaded by bootstrap and
Gradle. See `tools/OPTIONAL-SETUP.md` for the optional Python and Magisk tools.

The app has local build and inference checks; external game behavior is not
verified. The Docker harness has not been built or booted on the development PC.
See [recovery details](recovered/README.md) and [cloud setup](cloud-lab/README.md).

## License

The restored upstream app is MIT licensed, copyright 2025 Juancavr6; see
[LICENSE](LICENSE). Upstream provenance is documented in `recovered/README.md`.
