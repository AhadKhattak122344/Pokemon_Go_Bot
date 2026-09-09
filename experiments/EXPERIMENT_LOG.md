# Experiment log

Read this before every retry. Append new entries; do not overwrite a failed result
with a later success. Historical dates below are reporting dates when the original
execution date was not supplied. Raw/private output belongs only in `artifacts/`.

## Outcome index

| ID / reported date | Environment / attempt | Outcome | Evidence / implication |
|---|---|---|---|
| H01 / 2026-09-09 | Windows tests using system Temp | Reported failure; local Temp worked | Earlier handoff; isolate environment errors from code failures |
| H02 / 2026-09-09 | Docker/WSL Android without usable /dev/kvm | Reported unsuccessful | Earlier handoff; use native WHPX for local work |
| H03 / 2026-09-09 | API 34 modified baseline: Magisk su | Reported success | Supplied Project_Handoff.docx; not retested during migrations |
| H04 / 2026-09-09 | API 34 Pokemon GO ARM64 via ndk_translation | Reported SIGILL failure | Historical handoff; root success did not resolve translation crash |
| H05 / 2026-09-09 | Clean API 36 Pokemon GO | Reported login UI reached; two accounts failed sign-in | Historical handoff; decisive authentication logs missing |
| V01 / 2026-09-09 | Native API 36 boot and readiness | Verified success | Prior setup: Android 16/API 36, boot=1, Google packages present, ADB UID 2000 |
| V02 / 2026-09-09 | Installed lab status and diagnostics | Verified success, exit 0 | artifacts/setup-api36-20260909/; does not test app login |
| V03 / 2026-09-09 | Proxmox offline plan | Verified plan only, exit 0 | artifacts/proxmox-setup-plan-20260909-150832.json; no host contacted |
| R01 / 2026-09-09 | Current Pokemon GO cannot open | User-reported failure, not reproduced | Latest request; not enough evidence to distinguish crash from sign-in failure |
| P01 / 2026-09-09 | Proposed Proxmox/Bliss/root/modules/fingerprint stack | Not run; no working outcome established | [Preserved proposal](2026-09-09-user-proposal.md); prior technical review in ../docs/DEBUGGING.md |

## V01 / V02 details

- Device: `poke_api36_test`, `emulator-5556`, Android 16/API 36.
- Action: maintained Start-Emulator.ps1 followed by installed CLI status and diagnostics.
- Actual: WHPX usable; boot=1; x86_64 and arm64-v8a advertised; native bridge
  libndk_translation.so; ADB UID 2000; Google Play Services and Play Store present.
- Evidence: `artifacts/profile-Api36-1dfac8e35781496d98fcd9ec87848887.json`
  and `artifacts/setup-api36-20260909/` (local ignored outputs).
- Not tested: actual ARM instruction compatibility, certification, Pokemon GO launch/login.
- Decision: retain the clean baseline. Presence of a bridge or Google packages
  does not identify the cause of the user's current app failure.

## R01 next bounded experiment ? pending

- Question: does the current failure occur at install, process launch, native crash,
  or authentication, and what is its first decisive logged error?
- Before action: record app version, exact UI message/time, AVD name and serial;
  capture existing full/crash logs before any clearing operation.
- Change: none initially; preserve diagnostic evidence from one reproduction.
- Acceptance: a timestamped symptom correlated with app/process error evidence,
  or explicitly record that available logs cannot establish a cause.
- Proposed follow-up: choose one test based on that evidence. Do not replace the
  guest or install the attached module stack merely from the emulator hypothesis.
- Status: pending; no app/device state was changed for this repository migration.

## Layout migration ? 2026-09-09

- Checkpoint: Git tag `checkpoint/layout-before-android-lab-20260909` at `4972269`.
- Objective: move working package/config/tests and consolidate documentation.
- Device/VM/downloaded-asset changes: none.
- Verification: 92 tests passed in the migrated checkout and a fresh exported tree.
  Frozen offline sync passed in the fresh tree; installed `lab` resolves to
  `android_lab.cli:main`. Wheel/source build succeeded; separate wheel install
  loaded the packaged default config and `lab --help` from site-packages.
- Windows profile checks, both Bash syntax checks, merged Docker Compose config,
  280 archive hashes and 13 CLI help checks passed. No live Docker boot was run.
- Review caught missing Docker test/config COPY inputs; repaired before completion.
  All 92 tests also passed in a minimal copy of only the Docker COPY inputs
  at `artifacts/docker-context-smoke/`; this was not a Docker image build.
- Raw build output: `artifacts/python-build.log`; fresh tree: `artifacts/fresh-layout/`.
- Result: package/layout verification passed; Pokemon GO failure remains untested.
- Model: Terra/medium implementation worker; no Astra diagnosis/escalation.

## Template for the next attempt

### ID / YYYY-MM-DD HH:MM timezone ? short question

- Status: proposed / running / passed / failed / inconclusive / user-reported.
- Environment: device/AVD/serial, Android API/build, app version, bridge, root state.
- Hypothesis and acceptance condition:
- Prior evidence and attempted fixes:
- Exactly one changed variable (or read-only capture):
- Command/action and exit code:
- Expected versus observed result:
- Evidence: artifact paths; redact private account data from tracked notes.
- Interpretation/confidence (separate observation from inference):
- Revert/cleanup performed:
- Next decision and reason a retry would add evidence:
- Model/effort if Astra was used, bounded decision, outcome:
