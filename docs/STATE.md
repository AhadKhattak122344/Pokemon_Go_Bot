# Current state

Updated September 9, 2026.

Latest repository organization: September 14, 2026. See
[PROJECT_MAP.md](PROJECT_MAP.md) for retained components and cleanup destinations.

## Implemented in this checkout

- `android_lab.cli:main` is the installed `lab` entry point from the root Python project.
- Native profiles use stable AVD names/ports: clean API 36 `poke_api36_test` at
  emulator-5556; existing API 34 `baseline` at emulator-5554; separate debug
  `baseline-rooted` at emulator-5554. Startup applies no Magisk patches.
- Read-only `lab diagnostics` captures device/Google package state, full/crash
  logcat and screenshot. Partial failures get an explicit report and nonzero exit.
- `lab connect` selects and authorizes a configured TCP ADB endpoint.
- Proxmox `plan`, `preflight`, `deploy` are real registered commands. Mocked tests
  cover allocation, task ordering, auth/TLS, timeouts and failure journals. Deployment
  starts full clones of an existing template; Android readiness remains unverified.
- Root files are cleaned; archive data is excluded from builds and runtime imports.

## Supplied historical observations, not retested here

The user handoff reports working WHPX; confirmed Magisk su on modified API 34;
Pok?mon GO ARM64 translation SIGILL on API 34; API 36 reaches login but two
accounts fail sign-in; Docker/WSL lacks usable KVM on this host.

## Local setup verified September 9, 2026

The existing clean API 36 AVD was started with the maintained Start-Emulator
script. WHPX was available; `poke_api36_test` on `emulator-5556` passed boot,
Android 16/API 36, package-manager, Google Play Services and Play Store presence
checks. ADB UID was 2000. No root/image patches were applied. Installed CLI
`status` and read-only `diagnostics` both exited 0. Evidence is in local ignored
`artifacts/setup-api36-20260909/` and
`artifacts/profile-Api36-1dfac8e35781496d98fcd9ec87848887.json`.

Dependencies synced with the frozen lockfile. All 92 unit tests, Windows profile
checks, 280 archive hashes and 13 CLI help checks passed. A Terra/medium worker
prepared ignored `config/proxmox.json` with a fresh namespace and
`artifacts/proxmox-setup-plan-20260909-150832.json` (offline plan exit 0).
The Proxmox host/template/storage/network fields remain examples awaiting actual
deployment values. No Proxmox host was contacted. The emulator was left running.
User-supplied test APK/package/activity are pending; app acceptance is unverified.

## Remaining unknowns

The decisive API 36 authentication error, current app certification/compatibility,
a real Proxmox host and guest choice, Linux/KVM behavior, and fleet capacity.
No sign-in, root patch, or real Proxmox deployment is claimed by repository tests.
There is no canonical Android app module: it was removed in cbc1d35. Gradle
skeleton/export material is retained only as provenance.

## Current investigation

Pokemon GO 0.427.0 **opens** on the clean API 36 AVD (`poke_api36_test`, emulator-5556): Unity splash and `UnityMainActivity` resumed, no crash buffer. Google account picker appears and one existing Google account completes GMS OAuth. Niantic then shows **Failed to Sign In** (RETRY / Try a different account). Location permission was granted; that did not clear the dialog. Login is therefore **failed at Niantic**, not at process launch. Play certification was not separately read in the Play Store UI. The same APK on Magisk API 34 (`baseline-rooted`) shows splash then **SIGILL** in `UnityMain` after ndk_translation starts; Magisk `su` remains `uid=0` `u:r:magisk:s0`. Concealment modules were not installed. `lab experiment` captures before launch and refuses PIF/Shamiko zips. Track attempts in [the experiment log](../experiments/EXPERIMENT_LOG.md). Proxmox remains preparation-only.

## Layout migration verification

Checkpoint: `checkpoint/layout-before-android-lab-20260909` at `4972269`.
Package is now `android_lab/`, scenarios `config/`, tests `tests/`, Linux helpers
`tools/linux/`, Docker definitions `config/docker/`. The installed command remains
`lab`; no business logic was rewritten. All 92 tests passed in the checkout and
a fresh export. The wheel, isolated entry point and packaged default config passed.
Windows profile, Bash syntax, Compose configuration, archive hashes and CLI help
checks passed. No device state or downloaded VM/Android asset was changed.
See [experiment history](../experiments/EXPERIMENT_LOG.md) for exact scope.

## Fresh investigation after Grok session (September 9, 2026 EDT)

Uncommitted Grok work was preserved at `artifacts/pre-debug-20260909/` before edits.
The API 36 device was started and the installed Pokemon GO 0.427.0 was launched
once after a pre-capture. It remained in UnityMainActivity with an empty crash
buffer, then visibly displayed **Failed to Sign In**. This is fresh evidence,
not a classifier inference. See `artifacts/pgo-current-failed/screen.png` and
`artifacts/pgo-current-later.png`.

Play Store Settings > About explicitly displayed **Device is not certified**
(`artifacts/playstore-certification.png`). Its built-in Fix device issue flow
returned **Couldn't fix device certification issue** and recommended system
updates (`artifacts/playstore-certification-detail.png`). This is a demonstrated
compatibility limitation, not proof of the game's private backend rejection reason.
No account was selected/removed, no app/service data cleared, and no root/image
or identity modification was made in this investigation. AVD startup remained
unchanged. Earlier claims that OAuth completion or emulator detection were proven
are stronger than activity transitions and the generic failure dialog establish.

Experiment classification defects were corrected: timeout is not a sign-in
failure, previous foreground state is not proof a process survived, unrelated
Google-service logs are not a target-app integrity verdict, and map-log keywords
are not confirmed authentication. Account selection remains manual.

Verification after corrections: 115 unit tests passed; Windows profile/syntax
checks, 280 archive hashes, 15 documentation files and 14 CLI help paths passed.
`lab experiment --login --login-timeout 12` ran on emulator-5556 and exited 0;
report `artifacts/pgo-fixed-harness/experiment.json` correctly leaves authentication
unverified while the app is foregrounded. Its screenshot remained on splash during
that short observation. The earlier fresh screenshot establishes the sign-in
failure; this run does not assert it has recovered. No account taps occurred.
`lab proxmox plan` exited 0 with example host values only. Existing uncommitted
Grok work remains uncommitted alongside these fixes; its backup is preserved.

## Physical-device comparison confirmed by user

The user explicitly confirms the same login works in Pokemon GO on a physical
iPhone. This rules out a general account-login failure; the remaining investigation
concerns the Android/emulator sign-in path. The previously supplied website
screenshot alone did not establish game login, but this explicit confirmation does.
The emulator's not-certified result remains relevant without proving the private
backend rejection reason. Avoid account resets/cycling as speculative fixes.

## September 13, 2026: live observer implemented and tested

`lab observe` now streams timestamped process/activity samples and saves PNGs,
raw activity dumps, JSONL evidence, and a completeness report. It defaults to the
configured package. Optional launch is restricted to the configured component
after pre-capture. Errors preserve partial artifacts and produce a failure exit.
This is host-side observation; it does not implement a companion APK or hooks.

Fresh clean API 36 startup and Pokemon GO 0.427.0 launch succeeded. The screen
advanced to Google's account chooser; no account was selected. Authentication
is unverified in this run. No Shungo package or accessible Magisk was found.
A live 20-second observer run exited 0 with six complete samples: game process
present, Google account chooser foregrounded. Evidence:
`artifacts/live-20260913-observer/observe.json` and adjacent captures.

Validation: 126 tests passed, Windows profile/syntax checks passed. Dependency
sync succeeded using the local UV cache. Existing uncommitted work was retained.
New work: `android_lab/observe.py`, `tests/unit/test_observe.py`, CLI/command docs,
observer help verification, and [the explanation and live findings](../experiments/2026-09-13-live-integration.md).
Next: user selects intended account in the emulator and identifies whether to
install existing Shungo or build a new companion. Full automation is not complete.

## September 13, 2026: official Shungo installed

User selected installation of existing Shungo. Official 1.7.0 APK downloaded,
signature verified, installed successfully on emulator-5556. Notification
permission granted. Login opened auth.shungo.app in Chrome; user completed it,
and MainActivity displayed the dashboard. Start is disabled with a subscription
required message. Overlay permission remains off: automatic review rejected
the grant pending explicit approval. No root/image changes or automation run.

Static inspection establishes a WebView dashboard, Auth0 integration, foreground
InjectorService, root shell execution path, and an external injector download
path. Exact game-hook internals are unverified. See
[installation and build explanation](../experiments/2026-09-13-shungo-installed.md).
Next: resolve recognized subscription and explicit overlay approval; full testing
also needs a compatible rooted device and successful game login.

## September 13, 2026: resumed Pokemon GO login investigation

Read [LOGIN_READ_FIRST.md](LOGIN_READ_FIRST.md) before every further login test;
DEBUGGING.md now requires it. The ledger defines success as a playable map plus
a normal in-game interaction and prevents repeats without changed evidence.

Warm foregrounding and one data-preserving cold restart both produced Failed
to Sign In. The cold run showed Google sign-in activity transitions but no
decisive backend error or crash. Automatic time was enabled and no global HTTP
proxy was configured. No clock, account, image or identity changes were justified.

After a usage interruption the emulator was absent; the existing clean API 36
AVD was restarted successfully. Play Store loaded Pokemon GO with Play and
Uninstall, no Update button. Opening via Play progressed through splash to the
Google account chooser. This latest attempt awaits intended account selection;
it is not a fresh confirmed failure or a successful login. Evidence directories
use `artifacts/pgo-login-20260913-*` and are indexed in the read-first ledger.

Observer deadline bug fixed: do not start a sample in the last one-second window;
probes already started retain normal bounded ADB timeouts, preserving real errors.
Regression tests and full suite passed (129 tests). Live captures show correct
missing-device failure and complete captures after reconnection. This tooling fix
does not repair game authentication. No emulator/root or app-data patches made.

## Designated-account test and next required control

User explicitly authorized selection of one Google account for all game tests;
exact address is in ignored `artifacts/login-account.json`. Agent selected that
visible account, and Failed to Sign In returned. Five complete samples, process
running, crash buffer empty. Evidence: `artifacts/pgo-designated-account-*`.

Network/permissions inspection found validated Wi-Fi without guest VPN, no
custom Private DNS, Google Play installer source and granted Internet/location
permissions. Astra/medium read-only diagnosis found no decisive account-specific
error, returned OAuth status or decoded integrity verdict. GMS parse/key errors
are not safely attributable to this login. No settings changed as guesses.

Next meaningful test needs a certified physical Android, same designated account
and network, official game and one captured login attempt. If none is available,
publisher-side transaction diagnosis is needed. Full login remains unresolved.
Read-first ledger updated; archive/document/CLI checks and diff check passed.

## September 14, 2026: official runtime comparison, not a login fix

Separate API36.1 Play revision4 installed and tested on emulator-5558. Auto GPU
failed boot; software reached boot marker but display crashed. Disabling shared
slots was accepted yet failed with the same SurfaceFlinger assertion. All three
results are recorded in LOGIN_READ_FIRST and artifacts/api361-test. No account
login performed on that unstable guest. Existing API36 account/app data preserved.

New bounded test: separate API37.0 Play revision6, based on Google's documented
API37 revision5+ Google authentication/certification fix. Installation pending.
Google security-email device labels do not establish physical hardware, certified
boot, or Pokemon GO login. Requested playable-map acceptance remains unmet.

## September 14, 2026: experiment memory system added

Structured experiment templates, a tracked knowledge base, Codex session memory
and a validator were added from the latest pasted request. The files summarize
existing evidence without promoting proposals to verified results. The validator
blocks non-retryable suggestions such as API34 translation repeats, unchanged
API36 login retries, API36.1 display reruns, API37 auto/host boot repeats,
Docker without KVM, and archived concealment/identity stacks. This is host-side
knowledge management only; no emulator, account, Proxmox host or app state was
changed.

## September 14, 2026: resumed runtime tests and startup cleanup

API37 Play revision6 on emulator-5560 reached boot=1 with software graphics,
but display validation failed: repeated SurfaceFlinger SIGABRT at
hasReadColorBufferDma and screenshot capture returned no PNG. A second launch
changed only GLDirectMem to disabled; host confirmed override, same display
failure. Startup exit0 is boot/version evidence only. No API37 game login was
attempted. Both runs and failed dmesg access are captured in
artifacts/api37-test/resume-before and artifacts/api37-test/no-directmem.
The test AVD is stopped, and the original API36 account/app data is preserved.

Start-Emulator.ps1 now tracks only the launched process tree and checks creation
times before timeout cleanup. Test-Profiles.ps1 has mocked cleanup/PID-reuse
coverage. A live one-second timeout produced expected startup exit1, zero owned
emulator processes, and an absent serial on follow-up ADB inspection. Evidence:
artifacts/api37-timeout-cleanup-result.json. This verifies cleanup, not guest boot.

Final validation:134 Python tests passed; Windows profile/cleanup/syntax checks,
280 archive hashes,30 documentation files,15 CLI help paths and diff check passed. Current Proxmox config still contains pve.example.com and template9000;
real host/node/template requested from user. No live Proxmox creation, Android13
matrix, golden configuration or game-success result is claimed. Next step needs
actual host/template details or new compatible renderer/image evidence.

## September 14, 2026: fleet handoff and repository cleanup

User-supplied Fleet files were restored under tools/windows and the matrix stays
in config/fleet-matrix.json. Host-side fixes cover native command capture/timeouts,
selection, process ownership and game observation. All 134 Python tests and fleet/profile
host checks passed before the attempted create. Official API35 Play revision9
download completed. New-FleetAvds -SkipInstall then exited1 because its default
Matrix path evaluated with an empty PSScriptRoot. No new fleet AVD was created
by that command, and fleet display/game acceptance remains unverified. Preserve
artifacts/fleet-create-run.log and the F01 ledger; fix and rerun after resumption.

The user redirected work to cleanup. Moved .tmp, generated root egg-info and the
remaining misplaced experiments/config duplicate into
artifacts/_archive/cleanup-20260914, preserving 969 files (43,728,992 bytes) with
per-file SHA-256 verification. Android SDK/JDK/AVD trees, assets, archived Android
source/game reference, configuration, original logs/experiment notes and existing
instruction documents remain in place. No device, account or image change was
performed for cleanup. The separate sibling deepseek-harness was untouched.

README and PROJECT_MAP now index the project. Android-Lab.code-workspace provides
separate views for code/instructions, evidence, Android toolchains, downloaded
components and the recovered Android reference. Local artifacts/INDEX.md indexes
the retained logs; the cleanup manifest, hashes and original Git diffs live in
artifacts/repo-cleanup-20260914. Final post-cleanup validation is recorded in the
experiment ledger. Post-cleanup: 134 Python tests, installed CLI help, Windows
profile/fleet checks, 280 archive hashes, 32 documentation files, 15 CLI help paths,
and git diff --check all passed. All 969 moved files passed SHA-256 verification.
