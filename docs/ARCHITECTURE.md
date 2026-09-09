# Architecture

Root Python project -> editable android-cloud-lab distribution -> android_lab.cli:main.

- `adb.py`: selected-device subprocess transport, shell quoting, bounded calls,
  TCP connection/authorization and screenshots.
- `health.py`: bounded transport/boot/package-manager readiness.
- `diagnostics.py`: read-only capture and partial evidence reports.
- `cli.py`: parser, dispatch and app launch smoke/JUnit artifacts.
- `root.py`: explicit debug-ADB transitions with restoration tests.
- `location.py`: deterministic emulator geo routes for authorized QA.
- `proxmox.py`: validated JSON plan, token-auth HTTPS API, template checks,
  UPID polling and full-clone task journal.
- Windows scripts own native AVD startup. Linux Compose owns Docker startup and
  two cold-boot attempts. Do not mix those lifecycles on one emulator port.

No FastAPI, PostgreSQL, Redis, Celery, Frida, concealment or integrity-bypass stack
is part of the active implementation. Add services only for demonstrated needs.
X86 KVM acceleration and ARM-native application compatibility are separate concerns.

## Repository boundaries

`android_lab/` is the importable package; `config/` holds scenarios, routes and Docker definitions; `tests/` holds unit tests. `tools/windows/` owns native setup and `tools/linux/` owns container startup. `artifacts/` holds ignored runtime output; `experiments/` holds tracked dated findings. `.codex/agents/` remains at the root. `assets/` and `.tools/` contain existing inputs/toolchains and were not altered. `archive/` remains reference-only. The packaged `android_lab/default.yaml` is a wheel fallback, checked against `config/default.yaml`.
