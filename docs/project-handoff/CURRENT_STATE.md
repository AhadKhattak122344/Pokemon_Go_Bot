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

## Still unknown

The decisive API 36 authentication error, current app certification/compatibility,
a real Proxmox host and guest choice, Linux/KVM behavior, and fleet capacity.
No sign-in, root patch, or real Proxmox deployment is claimed by repository tests.
There is no canonical Android app module: it was removed in cbc1d35. Gradle
skeleton/export material is retained only as provenance.
