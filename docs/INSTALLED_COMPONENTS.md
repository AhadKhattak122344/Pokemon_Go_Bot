# Environment and validation scope

The September 9 change was made in the Windows checkout on `main`. Python tests
run through uv using Python 3.12.10. The SDK/JDK and AVD state remain under ignored
`.tools/`; their directory was not moved, patched, or recreated by cleanup.

The supplied handoff reports WHPX works, Docker lacks usable KVM on this host,
API 34 root is established, and API 36 reaches app sign-in but fails authentication.
These are attributed previous observations. Current session results live in
[the historical evidence](../experiments/2026-09-09-previous-migration-evidence.md).

Dependency installation and Git fetch required network-enabled execution in the
agent sandbox. This is an environment restriction, not a unit-test failure.
No Proxmox host, Google account, app sign-in, Docker emulator or device root
transition was exercised for the repository migration.

## Recorded local components

Python 3.12.10, pytest 8.3.5, PyYAML 6.0.2, setuptools 80.9.0; runtime/test versions are locked in uv.lock; the build backend is pinned in pyproject.toml. Windows SDK/JDK/AVDs stay under `.tools/`. ADB 37.0.1 and WHPX were verified in the prior setup. API 36 AVD `poke_api36_test` uses port 5556; API 34 `baseline` and `baseline-rooted` share port 5554 and cannot run together. API 36 boot, Google Play Services/Store presence and shell UID 2000 were verified. Package presence does not establish certification or app login. The exact current APK version is not recorded. No real Proxmox host or installed guest has been verified.
