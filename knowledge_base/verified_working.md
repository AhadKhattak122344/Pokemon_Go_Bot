# Verified Working Configurations

Last updated: 2026-09-14

## Native API 36 Baseline

Status: working for boot, package-manager readiness, Google package presence,
Pokemon GO process launch, diagnostics, and observation.

Evidence: `experiments/EXPERIMENT_LOG.md` entries V01, V02, V04, V08, V16.

Notes:

- AVD: `poke_api36_test`, serial `emulator-5556`.
- Pokemon GO 0.427.0 opens and reaches Google account/sign-in flow.
- This is not a playable-map success. Authentication remains unresolved.

## Observation Harness

Status: working for bounded read-only samples, screenshots, activity dumps, and
JSONL evidence.

Evidence: V08 observer verification and later L-series login attempts.

Notes:

- `lab observe` captures evidence but does not establish certification, sign-in,
  or gameplay.
- Launch mode only starts the configured component after pre-capture.

## Proxmox Offline Planning

Status: working as an offline plan and validation step.

Evidence: V03 and Proxmox unit tests.

Notes:

- `lab proxmox plan` derives deterministic locally administered MACs and SMBIOS
  UUIDs from a namespace UUID.
- It does not contact a Proxmox host, boot Android, or prove app compatibility.

## Official Shungo Installation

Status: installed and user login completed on the API 36 emulator.

Evidence: V09.

Notes:

- Dashboard loads.
- Start remains blocked by subscription/entitlement and overlay permission.
- Injector/game integration is unverified.
