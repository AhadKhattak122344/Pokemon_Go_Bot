# Fresh Pokemon GO diagnosis ? September 9, 2026 EDT

## Question and baseline

Can the existing game launch, and what exact failure is observable without
repeating Grok's root/translation experiments? Read the complete
`2026-09-09-session-actions.txt` first. Preserve dirty code in
`artifacts/pre-debug-20260909/`. Keep API 34 untouched and API 36 unrooted.

## Reproduction

1. No connected ADB devices initially. Start-Emulator.ps1 -Profile Api36:
   exit 0, Android 16/API 36 boot=1, ADB UID 2000, Google packages present.
2. `lab --config config/pokemongo.yaml diagnostics --package
   com.nianticlabs.pokemongo --out artifacts/pgo-current-pre`: exit 0.
3. `adb -s emulator-5556 shell am start -S -n
   com.nianticlabs.pokemongo/com.nianticproject.holoholo.libholoholo.unity.UnityMainActivity`:
   exit 0. No log clearing or account-selection tap.
4. Capture to `artifacts/pgo-current-post`: splash, resumed UnityMainActivity,
   crash buffer empty. Package 0.427.0, code 2026082702, ARM64,
   installer com.android.vending.
5. Later screenshot `artifacts/pgo-current-later.png`: **Failed to Sign In**.
   Still resumed and crash buffer empty. Full capture
   `artifacts/pgo-current-failed/`: exit 0.
6. Open existing Play Store, Settings > About. Screenshot
   `artifacts/playstore-certification.png`: **Device is not certified**.
7. Built-in Fix device issue result
   `artifacts/playstore-certification-detail.png`: **Couldn't fix device
   certification issue**; suggests system updates. No flash/reset performed.

## Interpretation

The process-open problem is not reproduced on API 36; sign-in failure is.
Certification is now measured, unlike Grok's earlier run. It is a relevant
compatibility limitation, but the generic game dialog does not expose the
backend rejection reason. Google activity transitions alone also do not prove
successful OAuth token exchange. No app-specific integrity verdict was obtained.
No supported control-device/account comparison is available yet.

Google documents that uncertified devices can have app/feature failures:
[certification guidance](https://support.google.com/android/answer/7165974?hl=en).
The publisher documents network/server causes for generic login errors too:
[login troubleshooting](https://niantic.helpshift.com/hc/en/6-pokemon-go/faq/113-i-received-the-unable-to-authenticate-or-failed-to-log-in-message/).
Do not assert certification is the sole cause from the dialog alone.

## New handoff configuration audit

| Requested layer | Actual status / disposition |
|---|---|
| Android boot, Google packages, ADB, capture/launch | Live verified on API 36 |
| Game authentication and gameplay | Sign-in failed; gameplay not verified |
| Device certification | Explicitly not certified; built-in repair unsuccessful |
| Proxmox client/template cloning | Existing CLI and mocked tests; real host/template/token still absent |
| Bliss guest / fleet | Not deployed; a VM is not proof of game compatibility |
| Root, concealment, handset identity / fingerprint stack | Not applied as speculative login fixes; no evidence of compatibility |
| FastAPI, PostgreSQL, Celery, Redis, metrics, ntfy | Proposal only, not existing configured services; adding these cannot establish guest/game acceptance |
| Claude harness | Existing requested Codex harness retained; not silently replaced |

The supplied new handoff contains undefined Python functions, TLS verification
turned off, and unsupported claims that fingerprints establish certification.
It is a proposal requiring design/validation, not an executable deployment spec.
No remote deployment was attempted, consistent with the user's earlier scope.

## VM alternative

The existing AVD already uses hardware virtualization (WHPX). A Proxmox Android
VM changes the host/guest implementation, but does not inherently provide a
certified physical handset or eliminate ARM translation on x86 hardware.
[Android VM acceleration](https://developer.android.com/studio/run/emulator-acceleration).
The supported comparison is the same account on an unmodified compatible physical
phone; the publisher excludes rooted devices and does not guarantee every
otherwise qualifying configuration:
[supported devices](https://niantic.helpshift.com/hc/en/6-pokemon-go/faq/92-supported-devices/).

## Next decision

Obtain the same-account result on a supported physical phone before changing
another guest image. Keep raw/private evidence in ignored artifacts. Do not
repeat root, account cycling, Google-data clearing, or translation replacement
without evidence that the intended change addresses the measured failure.

## Checker corrections and verification

Fixed false positives: old resumed state after process death, unrelated Google
integrity/Java-crash log attribution, synthetic failure after OAuth timeout, and
map-log keywords being treated as authenticated gameplay. Invalid timeouts are
rejected and readiness/capture failures now produce a report. Login watching no
longer taps the first account. These changes are in android_lab/experiment.py
and regression tests; the CLI help documents observation-only behavior.

Full suite: **115 passed** (exit 0), log
`artifacts/audit-experiment-20260909/pytest-attribution-fix.log`.
Windows profile/syntax, repository verifier and diff checks passed. Live corrected
command `lab --config config/pokemongo.yaml experiment --login --login-timeout 12
--out artifacts/pgo-fixed-harness` exited 0, classification foreground_ok,
authentication unverified, account_tapped false, splash screenshot. This tests the
capture code, not successful game authentication. Emulator left running.
No real Proxmox server exists in the supplied configuration; offline plan exit 0
at `artifacts/pgo-investigation-proxmox-plan.json` does not establish deployment.
Routine audit/implementation used one Terra/medium worker; no Astra escalation.
