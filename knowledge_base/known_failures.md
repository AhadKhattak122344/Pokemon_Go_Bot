# Known Failures - Do Not Retry Without New Evidence

Last updated: 2026-09-14

## Pokemon GO API 34 With ARM64 Translation

Status: failed.

Symptoms: `Fatal signal 4 (SIGILL)` in `UnityMain` after `ndk_translation`
initializes.

Evidence: `experiments/EXPERIMENT_LOG.md` entries H04 and F01.

Do not retry as a login or root-hiding fix. The observed failure is native
translation, and Magisk root did not resolve it.

Alternative: keep launch investigations on the clean API 36 baseline unless a new
device/runtime supplies different evidence.

## Clean API 36 Login Repeats

Status: failed for playable login with the designated account.

Symptoms: Pokemon GO reaches account/sign-in flow, then shows Failed to Sign In;
crash buffer remains empty.

Evidence: F02, F03/C01, L10-L17.

Do not repeat warm foregrounding, data-preserving cold restart, or selecting the
same account again without a changed variable. The next useful comparison is a
certified physical Android or publisher-side transaction diagnosis.

## API 36.1 Google Play Runtime Display

Status: failed display stability.

Symptoms: boot markers can pass, but SurfaceFlinger aborts with the same
GoldfishMapper readFromHost assertion and screenshot capture fails.

Evidence: L19-L21.

Do not treat boot completion as usable display readiness for this profile.

## API 37 Auto/Host Rendering First Boot

Status: failed initial boot.

Symptoms: ADB remained offline through the bounded startup window.

Evidence: L22.

Alternative: the planned L23 comparison changes only API37 GPU mode to software.

## Docker/WSL Android Without KVM

Status: reported unsuccessful.

Evidence: H02 and `docs/DEBUGGING.md`.

Do not repeat this host's software-emulated Docker path unless new evidence shows
usable `/dev/kvm` or equivalent acceleration.

## Archived Identity, Concealment, and Integrity Scripts

Status: rejected for active compatibility fixes.

Evidence: `docs/DEBUGGING.md`.

Do not execute archived identity/concealment/integrity scripts or treat string
changes as certification evidence.

## Pasted Play Integrity Bypass And Anti-Detection Runbook

Status: rejected.

Evidence: latest pasted implementation request and `codex_memory/attempted_approaches.json`
entry P02.

Do not implement or operationalize root-concealment modules, Play Integrity
bypass checks, device identity spoofing, ADB hiding, mock-location hiding,
behavioral anti-detection, or residential proxy masking for Pokemon GO.

Alternative: keep work to legitimate device-farm lifecycle automation, evidence
capture, official compatibility testing, a certified physical Android comparison,
or publisher-side diagnosis.
