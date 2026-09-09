#!/usr/bin/env bash
set -euo pipefail
deadline=$((SECONDS + ${1:-900}))
emulator_pid=${2:-}
delay=1
while (( SECONDS < deadline )); do
    if [[ -n "$emulator_pid" ]] && ! kill -0 "$emulator_pid" 2>/dev/null; then
        echo 'Emulator process exited before boot completed; see emulator.log' >&2
        exit 1
    fi
    state=$(timeout 5 adb -s emulator-5554 get-state 2>/dev/null || true)
    boot=$(timeout 5 adb -s emulator-5554 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
    if [[ "$state" == device && "$boot" == 1 ]]; then
        package=$(timeout 5 adb -s emulator-5554 shell pm path android 2>/dev/null | tr -d '\r' || true)
        if [[ "$package" == package:* ]]; then exit 0; fi
    fi
    remaining=$((deadline - SECONDS))
    if (( remaining <= 0 )); then break; fi
    if (( delay < remaining )); then sleep "$delay"; else sleep "$remaining"; fi
    if (( delay < 8 )); then delay=$((delay * 2)); fi
done
echo 'Timed out waiting for emulator boot' >&2
exit 1
