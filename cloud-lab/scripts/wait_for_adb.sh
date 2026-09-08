#!/usr/bin/env bash
set -euo pipefail
deadline=$((SECONDS + ${1:-900}))
delay=1
while (( SECONDS < deadline )); do
    state=$(timeout 5 adb -s emulator-5554 get-state 2>/dev/null || true)
    boot=$(timeout 5 adb -s emulator-5554 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
    if [[ "$state" == device && "$boot" == 1 ]]; then exit 0; fi
    sleep "$delay"
    if (( delay < 8 )); then delay=$((delay * 2)); fi
done
echo 'Timed out waiting for emulator boot' >&2
exit 1
