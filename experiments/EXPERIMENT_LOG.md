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
| V04 / 2026-09-09 | API 36 launch of installed Pokemon GO 0.427.0 | Verified process opens | Unity splash + `UnityMainActivity` resumed; no SIGILL in crash buffer. `artifacts/pgo-r01-launch2/` |
| V05 / 2026-09-09 | Magisk 30.7 live setup on `baseline-rooted` | Verified `su` uid=0 `u:r:magisk:s0` | Installer script exited 1 after ADB drop; Magisk still present. No Shamiko/PIF |
| F01 / 2026-09-09 | Same 0.427.0 APK on Magisk API 34 | Failed: SIGILL in UnityMain ~8s after splash | `artifacts/pgo-r01-34-launch/` and crash dump; Magisk did not prevent translation crash |
| F02 / 2026-09-09 | API 36 Google account picker then Niantic login | Failed: in-game "Failed to Sign In" | Google OAuth picker completed; Unity dialog RETRY. `artifacts/pgo-after-google-signin.png`, `artifacts/pgo-login-wait3/login.png`. Location was granted. No second account tried. |

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

## V04 details

- Device: `poke_api36_test`, `emulator-5556`, Android 16/API 36, ADB UID 2000, no Magisk.
- Package: `com.nianticlabs.pokemongo` 0.427.0, `primaryCpuAbi=arm64-v8a`, already installed.
- Action: `lab --config config/pokemongo.yaml experiment --launch` after a read-only pre-capture. No logcat clear until after pre-capture. No concealment zips.
- Actual: launcher resolved to `UnityMainActivity`; splash screenshot; activity still resumed minutes later. Crash buffer empty. Classification originally `launch_error` only because `am start` without `-W` omits `Status: ok`; classifier corrected to treat resumed activity as `foreground_ok`.
- Evidence: `artifacts/pgo-r01-capture/`, `artifacts/pgo-r01-launch2/launch.png`.
- Not tested: Google account sign-in, Play Protect certification.
- Decision: keep API 36 clean. This is the guest where the process opens.

## V05 / F01 details

- Device: `baseline-rooted`, `emulator-5554`, Android 14/API 34 Google APIs, userdebug.
- Action: existing `Install-Magisk.ps1` (temporary Magisk 30.7 live setup). Then `adb install-multiple` of the API 36 base+arm64 split APKs and one launch. No Shamiko, PIF, or DenyList.
- Magisk: `/debug_ramdisk/magisk -v` is `30.7:MAGISK:R`; `magisk su -c id` is `uid=0` `context=u:r:magisk:s0`.
- Game: splash appeared; `ndk_translation` aarch64 0.2.3 initialized; ~8s later `Fatal signal 4 (SIGILL)` in tid `UnityMain`. Launcher returned to the foreground. Magisk su still worked after the crash.
- Evidence: `artifacts/pgo-r01-34-launch/`, `artifacts/pgo-r01-34-sigill-crash.txt`.
- Decision: do not hide root or spoof integrity to paper over SIGILL. Use API 36 for process-open; Magisk stays on the debug API 34 image.

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
- Status: superseded by V04 (process opens on API 36) and F01 (API 34 SIGILL with Magisk still working).

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

Reusable starter files now live in `experiments/TEMPLATE/`. Copy that directory
for longer attempts, then append the concise tracked result here.

## F03 / C01 ? fresh API 36 reproduction and certification check

See [full dated evidence](2026-09-09-fresh-login-investigation.md).
Start, diagnostic capture and explicit launch commands exited 0. Game opens but
visibly fails sign-in; crash buffer empty. Play Store says Device is not certified;
built-in repair couldn't fix it. No account or image changes. The exact backend
failure reason is unknown. Earlier generic integrity/classifier signals are not
proof. The new fleet handoff is audited in the same note and is not a working stack.

## V06 ? corrected experiment harness

115 tests passed. Corrected observation-only login run exited 0 on API 36,
left authentication unverified and did not select an account; evidence
`artifacts/pgo-fixed-harness/`. This is a checker verification, not a game fix.
Unit tests now cover false attribution, timeout, readiness report, and no-tap
behavior. See the F03/C01 investigation note for the unresolved sign-in limitation.

## V07 ? user-confirmed physical-device control

- Date reported: September 9, 2026.
- User confirms the same login works in Pokemon GO on a physical iPhone.
- Status: user-confirmed game login; not independently operated by this agent.
- Earlier screenshot showed Trainer Central website login only; this subsequent
  explicit confirmation supplies the separate game-login control.
- Interpretation: a general account-login failure is ruled out by this control.
  The unresolved failure is specific to the Android/emulator sign-in path or its
  environment. This does not establish the exact backend rejection reason.
- Existing local evidence: clean API 36 launches then fails sign-in; Play Store
  reports not certified. Certification remains a candidate, not proven causation.
- Next decision: investigate device/platform differences; do not reset credentials,
  cycle accounts, or repeat generic account-recovery steps without new evidence.
- No commands, device mutations or new game login attempts in this update.

## V08 / September 13, 2026 EDT - live startup observation

- Environment: existing clean `poke_api36_test`, emulator-5556, API 36,
  Pokemon GO 0.427.0; no image/root changes.
- Hypothesis: the installed game can still open; authentication is a separate
  acceptance condition requiring user account selection.
- Initial `adb devices -l` attempts in the sandbox exited 1: ADB could not create
  its Android user directory. ANDROID_USER_HOME/ANDROID_SDK_HOME overrides did
  not fix it. Approved execution outside the sandbox exited 0 with no devices.
- Dot-sourcing Android-Environment.ps1 was blocked by execution policy; no
  device action occurred. Maintained startup via
  `powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api36 -TimeoutSeconds 180`
  exited 0. One changed variable: started the existing clean AVD.
- `lab --config config/pokemongo.yaml diagnostics --package com.nianticlabs.pokemongo --out artifacts/live-20260913-before`
  exited 0. Selected AVD name was independently checked with `emu avd name`.
- `lab --config config/pokemongo.yaml experiment --launch --out artifacts/live-20260913-launch`
  exited 0. One changed variable: launched installed game after pre-capture.
- Post-launch diagnostics to `artifacts/live-20260913-after` and
  `artifacts/live-20260913-settled` exited 0. Screenshots inspected: app splash,
  publisher splash, then Google account chooser. Crash buffer empty.
- No account selected; authentication remains unverified. No Shungo package
  was returned by package queries; no accessible Magisk binary detected.
- Raw output retained only under artifacts. No app/service data clearing,
  root patch, ART replacement, or account cycling. Emulator left running.
- Next decision: user completes account selection and clarifies existing
  commercial Shungo installation versus building a new companion.
- Explanation and scope: [live integration](2026-09-13-live-integration.md).

### V08 observer verification

- New implementation by Terra/medium worker; lead alone operated the emulator.
- `lab --config config/pokemongo.yaml observe --duration 20 --interval 3 --out artifacts/live-20260913-observer`
  exited 0. Read-only capture; six samples with no errors, target process present,
  Google account picker foregrounded. No authentication inference.
- `uv sync --extra test --offline` with local UV_CACHE_DIR exited 0; initial
  default-cache attempt failed for sandbox access and was not treated as success.
- `uv run pytest -p no:cacheprovider --basetemp artifacts/tmp/pytest-live-20260913`
  exited 0, 126 passed. Windows Test-Profiles.ps1 exited 0.
- Full Shungo automation remains unimplemented; missing integration contracts
  and pending user choices are described in the linked note.

## V09 / September 13, 2026 EDT - official Shungo install and login

- User authorized existing Shungo installation, then completed login manually.
- Environment: unchanged clean API 36 emulator-5556, Pokemon GO 0.427.0.
- Download: sandbox curl failed (exit 7); approved external curl fetched official
  download page, its JS endpoint, APK link and APK (each exit 0). aapt and
  apksigner verify exited 0. Version 1.7.0 / 170. No repackaging.
- Pre-capture `diagnostics --package com.shungo.app` exited 0. One change:
  `adb -s emulator-5556 install artifacts/shungo-20260913/shungo1.7.0.apk`
  returned Success, exit 0.
- `experiment --package com.shungo.app --launch` exited 0, screenshot showed
  notification permission dialog. `pm grant com.shungo.app android.permission.POST_NOTIFICATIONS`
  followed by observation exited 0 and showed MainActivity login screen.
- Tap on observed Login opened Chrome CustomTabActivity at auth.shungo.app.
  User logged in. Post-login observer exited 0 and screenshot showed dashboard,
  no recognized subscription, Start disabled, overlay permission missing.
- Attempted SYSTEM_ALERT_WINDOW grant was rejected by automatic approval review
  before execution. No indirect grant attempted. Separate settings inspection
  proceeded with permission off and exited 0; no settings changed.
- Raw evidence: `artifacts/shungo-20260913/`. Terra/medium worker inspected APK
  statically only; lead alone controlled device. Final static tools exited 0.
- Verified: APK installation, UI startup, user login, dashboard/settings rendering.
  Not run: injector, overlay, game automation. Missing root/compatible environment,
  recognized entitlement and overlay approval remain separate blockers.
- No runtime repository code changed; explanation/state/log updated. Details:
  [Shungo installation](2026-09-13-shungo-installed.md).

## L10-L15 / September 13, 2026 EDT - login investigation and resumption

- Required first read: [LOGIN_READ_FIRST.md](../docs/LOGIN_READ_FIRST.md), linked
  from DEBUGGING.md. Every next attempt must consult and update this ledger.
- Pre-capture diagnostics exited 0; `am start -W -n` returned HOT / Status ok,
  but screenshot showed Failed to Sign In. Observer exited 1 from a final 0.1s
  screenshot timeout; earlier evidence intact. Artifact: pgo-login-20260913-open.
- One changed variable: force-stop game then cold start, retaining data/accounts.
  Launch and 30s observer exited 0. Google activity appeared, then the same
  Failed to Sign In dialog; crash buffer empty. Artifacts: pgo-login-20260913-cold
  and pgo-login-20260913-cold-result. No reason to repeat cold restart as a fix.
- Read-only time/proxy checks: auto_time=1, http_proxy=null, UTC consistent.
  Target logs show integrity warmup and activity transitions, not a returned
  backend verdict. No speculative configuration changes made.
- Play Store check was rejected before execution because approval review reported
  exhausted usage. User reported reset and requested continuation. Retried same
  read-only store opening: device absent, observation exited 1 and retained report
  under pgo-login-20260913-store-resumed. This was not another game login failure.
- `powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api36 -TimeoutSeconds 180`
  exited 0; profile evidence profile-Api36-5cb65798391d4184abbae1c887d1e8ef.json.
- Official store opening via `am start -a android.intent.action.VIEW -d market://details?id=com.nianticlabs.pokemongo -p com.android.vending`
  plus observer exited 0. Store eventually showed Play/Uninstall, no Update.
  Artifacts: pgo-login-20260913-store-ready and pgo-login-20260913-store-loaded.
- Pre-capture then tap observed Play button (237,201): observer exited 0,
  splash progressed to Google account chooser. No account chosen by agent.
  Artifacts: pgo-login-20260913-evening-before, pgo-login-20260913-store-play,
  pgo-login-20260913-store-play-settled. Await user selection, then capture result.
- Terra/medium worker fixed late-sample timeout in observe.py and regression
  tests. Lead ran full suite: 129 passed, exit 0. No device operations by worker.
- No app/account data clearing, downloads, root/image changes or concealment.
  Only the running emulator is attached; asked user about physical Android control.

## L16-L17 / September 13, 2026 EDT - designated Google account

- User authorized agent to select only the specified Google account in future.
  Exact preference recorded privately in artifacts/login-account.json.
- Existing emulator-5556, clean API36, Pokemon GO0.427.0. Diagnostics before
  selection exited 0; screenshot showed chooser. Selected matching visible row
  using `adb -s emulator-5556 shell input tap 171 288` (exit 0).
- 20-second observer exited 0; five complete samples, PID3428 running,
  screenshot Failed to Sign In. Final diagnostics exited 0; crash buffer empty.
  Artifacts: pgo-designated-account-before, pgo-designated-account-selected,
  pgo-designated-account-result.
- Read-only dumpsys connectivity: default WiFi VALIDATED/NOT_VPN. Private DNS
  mode/specifier both null; package installer com.android.vending; Internet and
  fine/coarse location permissions granted. No changes justified by these checks.
- Astra/medium read-only diagnosis: no decisive account-specific auth error;
  Google activity return lacks status; integrity warmup lacks verdict; GMS
  parse/key errors predate attempt and are not tied to game rejection. No device
  operation by diagnostician, no escalation above medium.
- Interpretation: reproducible login failure with designated account; exact
  backend cause unknown. No further identical emulator retry. Next: certified
  physical Android with same account/network or publisher transaction diagnosis.
- Documentation/CLI/archive validator and git diff --check exited 0. No runtime
  code, permissions, accounts, app data, root or image changes this attempt.

## L18-L22 / September 14, 2026 EDT - separate official runtime testing

- L18: stable SDK catalog read, exit 0; API36 revision7 already latest in track.
  Official API36.1 Play revision4 installed successfully; source.properties and
  artifacts/sdk-api361-install.log retained. API36 baseline preserved.
- L19: Start-Emulator.ps1 -Profile Api361 -TimeoutSeconds 180 (default GPU auto)
  exited 1 at boot timeout. SurfaceFlinger SIGABRT in GoldfishMapper::readFromHost:
  Assertion failed: !rcEnc->featureInfo()->hasReadColorBufferDma.
  artifacts/api361-test/first-boot and getprop-20260914.txt retain evidence.
  Actual SDK full36.1, patch2026-01-05, release-key Google Play build.
- L20: only GPU changed to software. Start-Emulator.ps1 -Profile Api361 -Gpu
  software -TimeoutSeconds 180 exited 0 on boot/version checks, but screenshot
  capture failed and SurfaceFlinger repeated the assertion. Result FAILED display
  stability, not successful startup. Evidence software-boot and software-ready.
- L21: same image/GPU, added -DisableSharedSlots to Start-Emulator.ps1.
  Emulator accepted -feature -HasSharedSlotsHostMemoryAllocator; startup exit0
  again did not establish display readiness. Diagnostics partial: screenshot was
  not PNG, same SurfaceFlinger assertion. artifacts/api361-test/sharedslots-disabled
  and emulator-poke_api361_test-b9fd3ce3fa05417bb64fa25835c8b677.log.
  Rollback: flag is launch-only; do not repeat these failed renderer settings.
- L22 hypothesis: Google documents authentication/certification failures in
  unpatched API37 images and revision5+ repair. Stable catalog has API37.0 Play
  x86_64 revision6. Prepare a separate image/AVD, do not replace original account
  data. This is a fresh-device comparison, not a controlled single-variable login
  experiment. Source: https://developer.android.com/studio/run/emulator-troubleshooting
- First API37 installer command could not source environment helper because of
  PowerShell execution policy; SDK install did NOT run despite shell exit0.
  Corrected to explicit workspace SDK/JDK environment variables. sdkmanager
  'system-images;android-37.0;google_apis_playstore;x86_64' --channel=0 now running;
  log artifacts/sdk-api37-install.log. Result pending.
- Latest supplied attachment read: OCR/reasoning about Samsung variant and rooted
  phones. Screenshots show Google email labels, no certification/gameplay result.
  No device identity masking, Google account resets, guest root patches, or login
  attempt on unstable API36.1. Only emulator-5558 attached at resumption.
- L22 provisioning result: sdkmanager exited0. Installed source.properties says
  revision6, API37.0 extension22, emulator dependency36.5.11 (installed37.1.11).
  system.img 2809135104 bytes. API36.1 stopped using name-checked Stop helper,
  exit0. Separate Api37 profile/config added; Terra/medium worker made only host
  script/doc changes, profile and syntax checks plus diff check passed.
  New startup command: powershell -NoProfile -ExecutionPolicy Bypass -File
  tools/windows/Start-Emulator.ps1 -Profile Api37 -TimeoutSeconds 180.
- L22 boot result FAILED: exit1 after180 seconds, ADB offline. Diagnostics exit1
  with explicit missing/offline evidence, no readable guest crash buffer. Host
  graphics driver GTX1050Ti, WHPX operational, 4096MB RAM confirmed in generated
  hardware-qemu.ini. artifacts/api37-test/first-boot and log
  emulator-poke_api37_test-2e56000beafd471a9804bb193356c0f6.log. Starter stopped its
  emulator process on timeout. No login/account operations.
- L23: change only GPU mode for API37, same image/AVD. Command:
  powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1
  -Profile Api37 -Gpu software -TimeoutSeconds 180. Expected: responsive ADB and
  stable screenshot capture. Do not generalize API36.1 graphics results to API37.
- L23 first startup did NOT run: exit1 from occupied-port guard. L22 timeout had
  stopped the launcher but left its qemu child. Read-only console confirmed
  poke_api37_test on5560; name-checked Stop-Emulator Api37 exited0. Retried the
  identical not-yet-run software startup after cleanup. This is not a repeated
  guest test or account attempt. Host cleanup defect assigned for bounded fix.

## M01 / 2026-09-14 EDT - experiment memory and knowledge management

- Status: passed.
- Environment: repository-only documentation and validator change; no device,
  Proxmox host, account, app data, root, image or network operation.
- Hypothesis and acceptance condition: future Codex sessions need a compact
  memory layer that flags known failed approaches before repeating them.
- One changed variable: added tracked templates, knowledge base, Codex memory
  JSON/notes and `tools/validate_against_history.py`.
- Expected versus observed result: validator blocks API34/MagiskHide/PIF style
  suggestions and allows an unmatched certified-physical-Android capture plan.
- Evidence: `codex_memory/attempted_approaches.json`,
  `knowledge_base/known_failures.md`, `tests/unit/test_history_validator.py`.
- Interpretation: this is a guardrail over existing evidence, not new device or
  app compatibility proof.

## M02 / 2026-09-14 EDT - rejected bypass runbook recorded

- Status: rejected.
- Environment: repository-only memory update; no device, Proxmox host, account,
  app data, root, image, network, proxy or location operation.
- Hypothesis and acceptance condition: the newly pasted technical stack should be
  searchable as a non-retryable approach because it combines root concealment,
  Play Integrity bypass, identity spoofing, anti-detection and IP masking.
- One changed variable: added P02 to the machine-readable memory and known-failure
  knowledge base.
- Expected versus observed result: future validator checks should block terms
  from that stack and point to legitimate alternatives.
- Interpretation: this records a rejected proposal only; it is not implementation,
  validation, compatibility proof or live device evidence.

## L23 completion / 2026-09-14 EDT - API37 software display test

- Environment: poke_api37_test / emulator-5560, official API37 Play revision6, emulator37.1.11, software GPU, 4096MB.
- One variable: resume previously unvalidated software-rendering run; original AVD absent at start. No account/app/image edits.
- Start action: powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api37 -Gpu software -TimeoutSeconds 180; printed boot/version success, command session still awaiting process handles.
- ADB name/boot inspection exit0: correct AVD, boot=1. diagnostics --config config/pokemongo-api37.yaml --out artifacts/api37-test/resume-before exited1.
- Observed FAILED display: screenshot is not PNG; crash buffer records repeated SurfaceFlinger SIGABRT in GoldfishMapper::readFromHost with hasReadColorBufferDma assertion. This is not a game-login result.
- Evidence: artifacts/api37-resume-start.log, artifacts/api37-test/resume-before/{report.json,crash.txt,logcat.txt}. Screenshot unavailable and explicitly recorded as failure.
- Next: examine host graphics feature controls for a bounded compatibility test; do not repeat unchanged software mode. Proxmox config still points at example host, so no live Proxmox matrix run.

## L24 / 2026-09-14 EDT - disable GLDirectMem for one API37 launch

- Status: FAILED display stability; no game install/login attempted.
- Environment: same API37 Play revision6, software GPU, 4096MB, emulator37.1.11, emulator-5560.
- Hypothesis: installed image enables GLDirectMem; disabling the host direct-memory feature might avoid the observed graphics readback assertion. This was a hypothesis, not established causation.
- One changed variable: process-local ANDROID_EMULATOR_FEATURES=-GLDirectMem; same Start-Emulator command as L23. Host log explicitly confirms feature disabled.
- Command: powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api37 -Gpu software -TimeoutSeconds 180; exit0.
- Diagnostics: python -m android_lab.cli --config config/pokemongo-api37.yaml diagnostics --out artifacts/api37-test/no-directmem; exit1. No PNG; SurfaceFlinger SIGABRT with identical hasReadColorBufferDma assertion.
- Evidence: artifacts/api37-no-directmem-start.log, artifacts/api37-test/no-directmem/{report.json,logcat.txt,crash.txt,dmesg.txt,dmesg-exit.txt}; host log emulator-poke_api37_test-a8505a0b128346499d3e9de3310183de.log.
- Kernel capture adb shell dmesg exit1: klogctl permission denied, recorded without escalating guest root. Screenshot unavailable due to captured display failure.
- Rollback: name-checked Stop-Emulator.ps1 -Profile Api37 exit0 after each run. Feature override scoped to launcher shell; no image edits. Both startup sessions completed exit0 once emulator handles closed.
- L23 final startup exit0 confirmed; its boot success does not change failed display acceptance.
- Next: compatible renderer/image evidence or a real Proxmox host/prepared Android template, requested from user. Placeholder pve.example.com was not contacted. Do not repeat L23/L24 unchanged.

## T01 / 2026-09-14 EDT - startup cleanup regression

- Status: PASSED cleanup behavior; deliberate boot timeout is not a guest compatibility test.
- Change: track launched process descendants with creation-time checks, reject PID reuse and older orphan edges; cleanup only validated process handles. Existing occupied-serial/name protections preserved.
- Worker: Terra/medium, host code and mocked tests only; lead exclusively controlled AVD.
- Live command: powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api37 -Gpu software -TimeoutSeconds 1; expected exit1 observed.
- Immediate process inspection found zero owned API37 emulator processes; ADB showed transient offline entry. Follow-up adb devices -l exit0 had no serial. Test summary passed true.
- Evidence: artifacts/api37-timeout-cleanup.log, artifacts/api37-timeout-cleanup-result.json. No guest account/image changes; test AVD remains stopped.
- Initial validation: uv sync --extra test --offline exit0, lab --help exit0, full pytest133 passed exit0. Artifacts test-resume-20260914.log.
- Mocked profile checks and parser checks passed; repository verifier passed280 archive hashes,30 documentation files,15 CLI help paths. Final validation follows below.

### T01 final validation

- First final pytest:132 passed,1 failed because old test expected the previously untested API37 software path to remain allowed. Preserved generic-tag isolation with injected fixture history and added a separate L23/L24 known-failure assertion.
- Second full pytest:134 passed,exit0; artifacts/test-resume-final2-20260914.log.
- Windows checks caught intermittent floating-point rounding of large creation-time ticks. Replaced numeric division with UTC millisecond formatting; mocked precision/PID-reuse tests and script syntax then passed,exit0.
- Final verify_repository.py:280 archive hashes,30 documentation files,15 CLI help paths passed,exit0; artifacts/verify-resume-final-20260914.log. git diff --check exit0 (existing line-ending notices only).
- Files changed this turn: Start-Emulator.ps1, Test-Profiles.ps1, test_history_validator.py, STATE.md, LOGIN_READ_FIRST.md, EXPERIMENT_LOG.md, codex_memory/current_context.md and attempted_approaches.json. Prior uncommitted work retained.

## L25 / 2026-09-14 EDT - user-requested single rerun

- User explicitly requested: ok run it once. One unchanged API37 software run authorized despite history warning; no configuration-search loop.
- Environment: poke_api37_test / emulator-5560, API37 Play revision6, software graphics, 4096MB, emulator37.1.11.
- Changed variable: none; a requested reproduction, not a new repair hypothesis. Acceptance still requires usable display.
- Command: powershell -NoProfile -ExecutionPolicy Bypass -File tools/windows/Start-Emulator.ps1 -Profile Api37 -Gpu software -TimeoutSeconds 180.
- Startup: exit0 boot/version profile success only; artifacts/api37-once-start.log and profile-Api37-3edf9296c8d5495a8b11e1f76698be32.json.
- Diagnostics: python -m android_lab.cli --config config/pokemongo-api37.yaml diagnostics --out artifacts/api37-test/once; exit1.
- Result: FAILED display stability again. report.json records "Device did not return a PNG screenshot"; crash.txt records SurfaceFlinger SIGABRT in GoldfishMapper::readFromHost with Assertion failed: !rcEnc->featureInfo()->hasReadColorBufferDma.
- Evidence: artifacts/api37-test/once/{report.json,crash.txt,logcat.txt,screen.raw}; host log emulator-poke_api37_test-b7eb3b970ac4498395dbc4b81efc74b1.log.
- Cleanup: name-checked Stop-Emulator.ps1 -Profile Api37 completed with "OK: killing emulator, bye bye"; artifacts/api37-once-stop.log. No game login, account, image, root or Proxmox operation was performed.

## F01 / 2026-09-14 EDT - restore and execute supplied fleet scripts

- User requested all pasted Fleet scripts in their own correct files and a rerun;
  then asked to continue testing. Meaning of the additional masking request is
  pending clarification; no masking operation is part of this runtime test.
- Initial state: Start-Fleet, Install-FleetGame and Stop-Fleet were zero bytes at
  tools/windows; four populated copies were nested under experiments/config.
  Config matrix and Common/New helpers were already in canonical paths.
- Checkpoint: artifacts/fleet-input-20260914-180404 contains Git diffs/status,
  original scripts/matrix, pasted source, and misplaced-originals. Existing
  unrelated work and downloaded assets preserved.
- Changed variable: restore the supplied fleet harness, fixing host execution and
  evidence defects before attempting its new, separate AVD configurations.
  Each matrix entry changes several guest settings and is an exploratory case,
  not a controlled single-variable comparison against the old baseline.
- API35 provisioning: first sdkmanager attempt exited1 because the parent shell
  blocked Android-Environment.ps1 by execution policy. Corrected only the host
  invocation using process-scoped Bypass; SDK download exited0. Official Play
  x86_64 image API35 revision9 installed. Logs: artifacts/fleet-api35-install.log,
  fleet-api35-install-retry.log and adjacent exit files.
- Exact corrected command after loading Android-Environment.ps1:
  `.tools/android-sdk/cmdline-tools/latest/bin/sdkmanager.bat --channel=0
  'system-images;android-35;google_apis_playstore;x86_64'`.
- Early validation: uv sync --extra test --offline exit0; uv run lab --help exit0;
  full pytest134 passed exit0; Test-Profiles.ps1 exit0. Evidence:
  artifacts/fleet-{uv-sync,cli-help,pytest,test-profiles}.log.
- Next: finish helper regressions, create the three enabled fresh AVDs, run display
  checks, then install/observe the existing official APK set on passing guests.
  Live fleet boot/game outcomes remain pending at this checkpoint.

### F01 continuation and pause for cleanup

- Get-FleetTools and native helpers were hardened locally; Test-Fleet.ps1 exited0
  for selection, duplicate ports, bounded native stdout/stderr/exit handling,
  wrong-AVD protection and reserved-variable checks. A previously launched
  Terra/medium worker supplied a partial helper implementation; the lead completed
  it locally when worker continuation was unavailable. Host tests are not devices.
- `powershell -NoProfile -ExecutionPolicy Bypass -File
  tools/windows/New-FleetAvds.ps1 -SkipInstall` exited1 before creating AVDs:
  Matrix default Join-Path received empty PSScriptRoot. Evidence:
  artifacts/fleet-create-run.log and fleet-create-run-exit.txt. This is a host
  invocation failure, not failed Android boot or game compatibility.
- WHPX check passed and ADB device list was empty before create. No fleet startup,
  game installation/login, masking, root or image patch was performed. User then
  requested repository cleanup; fleet execution paused with this defect documented.

## C01 / 2026-09-14 EDT - preserve and organize repository

- User requested cleanup while retaining logs, experiments, Android builds and
  components, Pokemon game mechanics, and instruction/command Markdown.
- Environment: local Pokemon_Go_Bot checkout; no emulator/VM/account operations.
- Hypothesis/acceptance: archive generated scratch/duplicate files, preserve
  valuable bytes and evidence paths, and make retained material easy to navigate.
- Changed variable: directory organization plus navigation docs/workspace only;
  runtime source/configuration and existing instruction documents preserved.
- Before moves: Git status, staged and unstaged binary patches saved under
  artifacts/repo-cleanup-20260914. An initial all-candidate inventory encountered
  Windows access restrictions on dist and on a scratch test directory in the
  other execution context. No permissions changed; dist was retained in place.
- Actual moves: .tmp, android_cloud_lab.egg-info and experiments/config to the
  corresponding paths beneath artifacts/_archive/cleanup-20260914. Every source
  and destination was resolved and checked inside the repo before Move-Item.
- Result: all 969 moved files, 43,728,992 bytes verified by SHA-256 and timestamp.
  File-path/size/mtime inventories of .tools, assets, archive and config unchanged.
  SDK images were not rehashed for this check; historical archive hashes get the
  separate repository verifier. No file was deleted. Experiment/raw-log paths in
  artifacts remain available; references to old .tmp scratch paths can be resolved
  through the cleanup move manifest.
- Evidence: artifacts/repo-cleanup-20260914/{move-manifest.json,
  preserved-before.json,preservation-result.json}; this is local ignored evidence.
- Navigation: README, docs/PROJECT_MAP.md, Android-Lab.code-workspace and local
  artifacts/INDEX.md. Original command/instruction Markdown and historical source
  filenames were kept; the map explains the flattened game's misleading names.
- Next: post-cleanup host tests and documentation checks; fleet creation remains
  paused on the F01 default-path defect, with no guest success claim.

### C01 final validation

- Full pytest: 134 passed, exit 0; installed lab --help exit 0.
- Test-Profiles.ps1 and Test-Fleet.ps1: exit 0. These are host/mocked checks.
- Repository verifier: 280 archive hashes, 32 documentation files, 15 CLI help
  paths passed, exit 0. git diff --check exit 0.
- Evidence: artifacts/repo-cleanup-20260914/{pytest.log,cli-help.log,profiles.log,
  fleet-host.log,repository-verify.log,diff-check.log,preservation-result.json}.
- Outcome: requested organization complete; no file deleted, existing unrelated
  staged/unstaged edits retained, and no live device action performed for cleanup.
  Fleet runtime work remains separately paused at the documented F01 defect.

## F02 / 2026-09-14 EDT - resume automated fleet tests

- User requested continued automatic testing and implementation. Original baseline
  AVDs/accounts and the cleanup archive are preserved; new outputs go under artifacts.
- Changed variable: resolve default Matrix/Summary paths in script bodies rather
  than parameter initializers. Added DryRun path/selection previews and regression
  tests invoking all four entry points from a foreign working directory.
- Host regression: Test-Fleet.ps1 exit0; artifacts/fleet-auto-20260914/host-tests.log.
- Live action: powershell -NoProfile -ExecutionPolicy Bypass -File
  tools/windows/New-FleetAvds.ps1 -SkipInstall, exit1. Default path now resolves;
  avdmanager rejects missing tools-directory property before AVD creation.
  Evidence: artifacts/fleet-auto-20260914/{create.log,create-exit.txt}.
- One subsequent correction: use com.android.sdkmanager.toolsdir for avdmanager,
  retaining com.android.sdklib.toolsdir for sdkmanager, as their installed .bat
  launchers specify. Retry is justified by that direct local evidence.
- Property correction result: create-fixed.log exit1 after successfully creating
  fleet_api35_pixel8 using available pixel_7. API36/API37 requested only unavailable
  Pixel8/9 profiles; the SDK reports none of those names. Add the same Pixel7/6
  fallback already used by the API35 case. This preserves each image/port and the
  new API35 AVD; no Force recreation. Persist available profiles and incremental
  creation summaries so partial progress remains reviewable.
- Creation completed exit0: create-fallback.log; all three AVDs use the available
  pixel_7 hardware profile, recorded in fleet-create-20260914-224611/summary.json.
- First boot batch: Start-Fleet.ps1 -MaxParallel 2 -ColdBoot -TimeoutSeconds 180
  -SettleSeconds 15, exit1. API35 display_ok with valid PNG and no captured display
  assertion; API36 boot_timeout and name-checked stop. API37 boot_timeout after
  rejecting angle_indirect and falling back to auto, then waiting on a host crash
  reporting dialog. Feature overrides were accepted. API37 owned-process cleanup
  requested; on resumption no emulator/qemu processes were present (including
  the formerly passing API35). No game test had yet run.
- Evidence: artifacts/fleet-auto-20260914/{start.log,start-exit.txt},
  artifacts/fleet-start-20260914-224642 and artifacts/fleet-latest.json.
- Next controlled host change: automatic sequential testing through Run-FleetTests,
  with a per-case report and stop verification. API36 concurrency changes from two
  starts to one. API37 GPU changes to supported swangle while keeping its feature
  overrides. Crash-report-mode never avoids consent dialogs in unattended runs;
  this is also a changed host launch flag, not a single-variable guest experiment.
  GPU preflight now rejects unsupported modes. Fixed PS5.1 JSON array nesting so
  the runner recognizes owned launches and the installer matches individual AVDs.
