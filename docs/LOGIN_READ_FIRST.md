# READ FIRST: Pokemon GO login investigation

Before another login/device experiment, read this file, STATE.md, DEBUGGING.md
and ../experiments/EXPERIMENT_LOG.md. Do not repeat a failed attempt unless a
new observation changes its hypothesis. Update this file after every attempt.

## Success condition

The intended existing account reaches the playable game map, remains running,
and supports a normal in-game interaction. A splash screen, resumed activity,
Google account picker or Shungo login is not success. Record actual screenshots
and process/crash evidence; never label an unobserved login successful.

## Established observations

- User explicitly authorized future selection of one designated Google account.
  Its exact email is stored locally in ignored `artifacts/login-account.json`.
  Match that account in the visible chooser; do not select another account or
  ask the user to select the same designated account again. Never change the
  account merely because the game suggests trying a different one.

- Clean `poke_api36_test`, emulator-5556, API 36, Pokemon GO 0.427.0 opens.
- Previous API 36 tests showed Failed to Sign In. Play Store explicitly showed
  Device is not certified; its built-in repair failed. This does not prove the
  exact backend reason for the game's rejection.
- Rooted API 34 hit native ARM translation SIGILL. Do not repatch it for login.
- User confirmed the same account works in the game on a physical iPhone.
- Shungo 1.7.0 is installed and user login succeeds. Its Start is disabled by
  an unrecognized/missing subscription. It has not injected into the game.
- Shungo overlay grant was rejected by approval review. Do not grant it without
  explicit approval or use it as a speculative Pokemon GO login repair.

## Attempts, September 13, 2026

| ID | One change / question | Observed result | Evidence / decision |
| --- | --- | --- | --- |
| L10 | Bring existing Pokemon GO task to foreground after preserving logs | am start reports HOT / Status ok; screenshot says Failed to Sign In; PID 4207 remains present | artifacts/pgo-login-20260913-before and artifacts/pgo-login-20260913-open. No gameplay. |
| L11 | Read-only time/proxy/error inspection | auto_time=1, http_proxy=null, device UTC agrees with current host date/time; no decisive target login error in retained log | artifacts/pgo-login-20260913-failed. No basis to modify clock/proxy. |
| L12 | Force-stop only game, then cold start preserving data/accounts | COLD launch succeeded; Google sign-in activity appeared, then Failed to Sign In returned within 30 seconds; crash buffer empty | artifacts/pgo-login-20260913-cold and artifacts/pgo-login-20260913-cold-result. Do not repeat this restart as a fix. |
| L13 | Check official Play Store update eligibility | Initial command was rejected before execution when approval-review usage was exhausted; resumed attempt found emulator absent | artifacts/pgo-login-20260913-store-resumed. Restart existing AVD then complete this unperformed store check. |
| L14 | Restore AVD and allow official listing to load | Store displays Pokemon GO with Uninstall and Play; no Update button visible | artifacts/pgo-login-20260913-store-loaded. No available update is demonstrated; no APK replacement justified. |
| L15 | Launch via Play Store after the AVD restart; wait through splash | Process remains running and reaches Google account chooser | artifacts/pgo-login-20260913-store-play and artifacts/pgo-login-20260913-store-play-settled. Pending intended account selection; not login success or a new confirmed failure. |
| L16 | Select the user's explicitly designated Google account from the visible chooser | Failed to Sign In reproduced, game PID3428 remained, crash buffer empty | artifacts/pgo-designated-account-before, pgo-designated-account-selected, pgo-designated-account-result. User also reported previous selection failed. |
| L17 | Read-only network, installer and permission checks | Active Wi-Fi network VALIDATED/NOT_VPN; Private DNS mode/specifier unset; installer com.android.vending; Internet and both location permissions granted | pgo-designated-account-result/connectivity.txt and target-package.txt. No justified DNS/permission change. Does not prove the game backend accepted requests. |
| L18 | Read build/patch level and official stable SDK catalog | Current API36 image revision7 has patch2025-07-05; same-track latest is revision7. Catalog offers separate API36.1 Google Play revision4 | artifacts/sdk-stable-list-login.txt. Test new official runtime separately; no in-place patch of existing AVD. |

L10 also found an observer defect: a final sample began at elapsed 7.922 of 8
seconds and its 0.1-second screenshot timeout made collection partial. This is
a tooling failure, not proof of game crash/disconnection. Earlier PNGs are valid.

## Next bounded test

L19 planned: separate `poke_api361_test` on emulator-5558 using official
`system-images;android-36.1;google_apis_playstore;x86_64`. Preserve API36 AVD.
Hypothesis: a newer official Android runtime may change compatibility; this is
not certification evidence or a promised fix. Download log:
`artifacts/sdk-api361-install.log`. Establish actual build, boot, app installation
and designated-account login independently; record fresh-device setup as a
confounder. Do not copy account tokens or claim a controlled runtime-only change
if testing starts with fresh user data.

September 14 L19 update: image revision4 installed, actual SDK36/full36.1,
security patch2026-01-05. Initial graphics `auto` repeatedly crashes SurfaceFlinger
with `Assertion failed: !rcEnc->featureInfo()->hasReadColorBufferDma`; boot is
incomplete. Evidence `artifacts/api361-test/first-boot/crash.txt`, partial capture
report and `getprop-20260914.txt`. This is a guest boot failure, not game login.
L20 next: change only GPU mode from auto to software, keeping same AVD/image and
other launch flags. Preserve failed logs and compare boot/screenshot readiness.

L20 result: software mode reached boot=1 and version checks passed, but later
SurfaceFlinger again aborted with the same assertion and screencap failed.
`software-boot/` and `software-ready/` diagnostics are partial; not a stable boot.
Do not mistake the boot-complete marker for a usable display.

L21 next: keep software mode and disable only emulator feature
HasSharedSlotsHostMemoryAllocator for this launch. Installed advancedFeatures.ini
enables it. Published renderer source conditions ReadColorBufferDma support on
that feature plus direct memory; this is an evidence-based compatibility
hypothesis, not proof about the installed renderer build. No guest image patch.

L21 result: feature override was accepted (emulator log confirms disabled), but
SurfaceFlinger still aborted on the same assertion and screenshot capture was
not PNG. Start script exit 0 reflected the boot marker only; usable display failed.
Evidence: `artifacts/api361-test/sharedslots-disabled/report.json`, `crash.txt`,
and emulator log `emulator-poke_api361_test-b9fd3ce3fa05417bb64fa25835c8b677.log`.
Do not repeat auto/software/shared-slots experiments without new evidence.

L22 next: separate official API37.0 Google Play x86_64 revision6. Google's
[emulator troubleshooting](https://developer.android.com/studio/run/emulator-troubleshooting)
documents Google service authentication/certification failures on unpatched API37
images and recommends revision5 or newer. This does not prove the cause on API36
or promise Pokemon GO support. Check display stability before adding the account.
The supplied security-email screenshots establish different labels only; neither
certification nor playable game login is shown. No identity masking performed.

## External comparison if official runtime tests fail

Compare a certified physical Android using the designated Google account,
official game and same network, one captured login attempt. No such device is
currently connected. If unavailable, obtain publisher diagnosis of the failed
transaction; do not send raw logs/tokens without review. Account selection is
authorized and has now been explicitly tested by the agent. The store
offers Play, not Update. The cold-restart hypothesis failed in L12. Retained
logs show integrity-service warmup and Google activity transitions, but no
decoded integrity verdict or decisive backend rejection reason. Do not equate
those transitions with successful OAuth or the warmup with passing integrity.

### Diagnostic review after L16/L17

Astra/medium inspected the retained logs and found no decisive account-specific
error. Google activity-result callback is logged without its status. GMS
AppCertManager parse/key errors also predate this attempt and occur near a
weather-provider failure, so they are not proof of the game's rejection reason.
No further unchanged login retry is justified by these logs. Relevant evidence:
`artifacts/pgo-designated-account-result/logcat.txt` lines 52189 (callback),
44965-45212 (integrity warmup), 52451-52493 (unattributed GMS errors).

## Rules for each new attempt

Record timestamp, serial/AVD, app version, hypothesis, one changed variable,
exact action and exit status, expected result, actual visible result, private
artifact path, interpretation, rollback and next decision. Keep raw accounts,
tokens and logs in ignored artifacts. Do not clear account/service data, replace
ART, spoof device identity, or install concealment modules as guesses. Escalate
to a compatible device or publisher diagnosis when evidence demands it.

L22 result: API37 revision6 auto/host rendering never brought ADB online within
180 seconds; startup exit1, diagnostics exit1 partial. Host log shows graphics
initialization on GTX1050Ti; WHPX operational and 4096MB guest RAM. No guest
crash evidence was obtainable while offline. artifacts/api37-test/first-boot and
emulator-poke_api37_test-2e56000beafd471a9804bb193356c0f6.log. Account not added.
L23 next: change only this API37 guest's GPU mode to software, which avoids the
host graphics driver selected in L22. Unlike API36.1 L20, this tests the different
API37 image. Stop after bounded boot and display validation; do not treat a boot
marker or a different email label as authentication success.

L23 completion September14: resumed API37 software boot reached boot=1 and
passed profile checks, but diagnostic capture exit1: no PNG and repeated
SurfaceFlinger SIGABRT at hasReadColorBufferDma. Evidence:
artifacts/api37-test/resume-before. No login attempted. Do not repeat unchanged
software mode as a repair. Investigate a targeted host graphics feature change.

L24: same API37 software launch, process-local ANDROID_EMULATOR_FEATURES=-GLDirectMem.
Host confirmed override, startup exit0, diagnostics exit1 with identical
SurfaceFlinger SIGABRT and invalid PNG. dmesg denied to shell UID.
artifacts/api37-test/no-directmem retains evidence. Guest stopped by name-checked
helper exit0; original API36 data preserved. No account/login operation.
Both L23 and L24 failed display acceptance. Do not rerun unchanged settings.
