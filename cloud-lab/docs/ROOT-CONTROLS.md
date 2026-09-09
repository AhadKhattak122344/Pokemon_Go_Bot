# Explicit emulator debug-root controls

From the root after loading the Android environment:

```powershell
uv run lab root status
uv run lab root enable
uv run lab root disable
uv run lab root self-test
```

Set `LAB_SERIAL` or select a YAML scenario for the intended owned debug emulator.
`status` only probes; it does not run `su`. Enable/disable uses `adb root`/`adb unroot`,
waits for reconnect and verifies numeric UID. Self-test restores the original ADB
privilege in a finally block. Each action writes a JSON report. Unsupported builds
and physical devices are rejected before changes. Do not run transitions concurrently.

ADB daemon privilege is distinct from app-level Magisk `su`. Optional unavailable
probes are reported as unknown. Nothing here patches boot images or hides root.
The separately available [Windows Magisk setup](../../tools/windows/OPTIONAL-SETUP.md)
is only for the owned API 34 debug image and requires explicit invocation.

The supplied handoff already reports root on the modified `baseline` AVD; do not
repatch it to fix ARM translation SIGILL. Keep `poke_api36_test` clean until its
ordinary authentication failure is understood. Historical live-root reports from
earlier sessions are not current migration verification evidence.
