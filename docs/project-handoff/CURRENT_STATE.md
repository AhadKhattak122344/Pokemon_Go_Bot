# Current state

Updated September 9, 2026.

## Implemented in this checkout

- `orchestrator.cli:main` is the installed `lab` entry point in the root uv workspace.
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
prepared ignored `cloud-lab/config/proxmox.json` with a fresh namespace and
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
