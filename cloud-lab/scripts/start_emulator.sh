#!/usr/bin/env bash
set -euo pipefail
mkdir -p /artifacts
emulator_pid=''
relay_pid=''
cleanup() {
    trap - EXIT INT TERM
    if [[ -n "$emulator_pid" ]]; then kill "$emulator_pid" 2>/dev/null || true; fi
    if [[ -n "$relay_pid" ]]; then kill "$relay_pid" 2>/dev/null || true; fi
    adb kill-server >/dev/null 2>&1 || true
    wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
if [[ "$EMULATOR_ACCEL" == on && ! -r /dev/kvm ]]; then
    echo 'KVM profile requires a usable /dev/kvm' >&2
    exit 1
fi
adb -L tcp:0.0.0.0:5037 start-server
# The emulator binds guest ADB to loopback. Forward a separate container port.
socat TCP-LISTEN:5559,bind=0.0.0.0,reuseaddr,fork TCP:127.0.0.1:5555 &
relay_pid=$!
for attempt in 1 2; do
    emulator -avd "$AVD_NAME" -port 5554 -no-window -no-audio -no-snapshot \
        -gpu "$EMULATOR_GPU" -accel "$EMULATOR_ACCEL" -memory 4096 -cores 4 \
        >>/artifacts/emulator.log 2>&1 &
    emulator_pid=$!
    if /opt/lab/scripts/wait_for_adb.sh "$BOOT_TIMEOUT"; then break; fi
    kill "$emulator_pid" 2>/dev/null || true
    wait "$emulator_pid" 2>/dev/null || true
    emulator_pid=''
    if [[ "$attempt" == 2 ]]; then echo 'Both cold boots failed' >&2; exit 1; fi
done
wait "$emulator_pid"
