# Environment and validation scope

The September 9 change was made in the Windows checkout on `main`. Python tests
run through uv using Python 3.12.10. The SDK/JDK and AVD state remain under ignored
`.tools/`; their directory was not moved, patched, or recreated by cleanup.

The supplied handoff reports WHPX works, Docker lacks usable KVM on this host,
API 34 root is established, and API 36 reaches app sign-in but fails authentication.
These are attributed previous observations. Current session results live in
[project-handoff/EVIDENCE.md](project-handoff/EVIDENCE.md).

Dependency installation and Git fetch required network-enabled execution in the
agent sandbox. This is an environment restriction, not a unit-test failure.
No Proxmox host, Google account, app sign-in, Docker emulator or device root
transition was exercised for the repository migration.
