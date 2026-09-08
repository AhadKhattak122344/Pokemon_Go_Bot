# RegiBot: restored Android project

This is the working source project. Open this directory in Android Studio, or use
the PowerShell scripts in `../tools/`. See `../START-HERE.md` for exact commands.

## Build status

- Debug APK compilation, JVM unit test, and Android lint completed successfully.
- Android lint reports 119 warnings and no errors; warnings remain in the original
  UI, dependency declarations, and lifecycle code.
- Two Android instrumentation tests passed on an API 30 x86 emulator, including
  actual inference with all three detectors, the classifier, and the predictor.
- Installation and launch were verified separately after instrumentation cleanup.
- The static recovery audit has no unresolved resource references or missing models.

The debug APK is copied to `../artifacts/RegiBot-debug.apk` by `Build-App.ps1`.
Device-test results are in `app/build/reports/androidTests/connected/debug/`.
Lint results are in `app/build/reports/lint-results-debug.html`.

## Restored inputs

The parent folder was a flat export with scrambled filenames: Java source appeared
inside XML and PNG files, and build configuration appeared inside HTML files.
`recovery-map.csv` records the initial 62 recovered files and their source hashes.
Some recovered files were subsequently revised.

Missing resources and all five real model binaries were restored from
[Juancavr6/RegiBot commit f242ee1](https://github.com/Juancavr6/RegiBot/tree/f242ee151a5447e4cfe83db4ee9090459cc23503),
under `app/app/src/main/`. `upstream-resources.json` records the 44 added resources;
the default/night theme files were also corrected to their original qualifiers.
`models.sha256` records the original Git LFS hashes, verified against every download.
The build now rejects missing or changed models before packaging. The actual binary
assets are included here; a Git LFS pointer alone cannot pass the build.

The upstream MIT license is preserved in `LICENSE`. `docs/ORIGINAL-README.md` is
historical upstream documentation, not a current test report.

## Code revisions

- Consolidated service commands; repeated play cannot create a second live worker.
- Paused workers wait rather than spin; stop wakes them and interrupts the worker.
- Cancellation is respected during startup and is not logged as a crash.
- Overlay creation is idempotent; cleanup handles missing clients and unattached views.
- The overlay service is not exported to unrelated apps.
- Priority edits refresh the active matching order immediately.
- Model file descriptors are closed reliably; model wrappers support explicit cleanup.
- Compile SDK is 35 to match the existing dependencies. Supported native ABIs remain
  ARMv7, ARM64, and x86. Adding x86_64 would leave the MediaPipe native library missing.

## Limits

This establishes a buildable and locally testable app. Screenshot/gesture cancellation,
fragment binding lifetime, and long-running model resource management still deserve
runtime review. The verification does not exercise external game clients or servers.
The supplied cloud/attestation documents were reference material; the app build does
not depend on their missing external modules, fabricated API endpoints, or keyboxes.
