#!/usr/bin/env bash
# Exit 0 means the automated checks passed, not that deployment is accepted.
# Exit 1 means a check failed; exit 2 means a usage/connection error.
set -uo pipefail
# Keep Git Bash from rewriting Android paths passed to the Windows adb.exe.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

if [ "$#" -gt 1 ]; then echo "Usage: $0 [ADB_SERIAL_OR_HOST:PORT]" >&2; exit 2; fi
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if command -v adb >/dev/null 2>&1; then
  ADB=adb
elif [ -x "$ROOT_DIR/.tools/android-sdk/platform-tools/adb" ]; then
  ADB="$ROOT_DIR/.tools/android-sdk/platform-tools/adb"
elif [ -x "$ROOT_DIR/.tools/android-sdk/platform-tools/adb.exe" ]; then
  ADB="$ROOT_DIR/.tools/android-sdk/platform-tools/adb.exe"
else
  echo "FAIL: adb is not on PATH and no repository-local adb was found." >&2
  exit 2
fi

ADB_ARGS=()
if [ "$#" -eq 1 ]; then
  case "$1" in
    *:*)
      connection="$("$ADB" connect "$1" 2>&1)" || { printf 'FAIL: %s\n' "$connection" >&2; exit 2; }
      case "$connection" in *failed*|*unable*|*cannot*) printf 'FAIL: %s\n' "$connection" >&2; exit 2 ;; esac
      ;;
  esac
  ADB_ARGS=(-s "$1")
else
  devices="$("$ADB" devices)" || { echo "FAIL: Unable to list ADB devices." >&2; exit 2; }
  serials=()
  while IFS=$'\t' read -r serial state; do
    state="${state//$'\r'/}"
    [ "$state" = device ] && serials+=("$serial")
  done <<<"$devices"
  if [ "${#serials[@]}" -ne 1 ]; then
    echo "FAIL: Specify a serial; expected one authorized device, found ${#serials[@]}." >&2
    exit 2
  fi
  ADB_ARGS=(-s "${serials[0]}")
fi

failures=0
check() {
  local label="$1"; shift
  if "$@"; then printf 'PASS: %s\n' "$label"; else printf 'FAIL: %s\n' "$label"; failures=$((failures + 1)); fi
}
shell() { "$ADB" "${ADB_ARGS[@]}" shell "$@"; }
root_shell() {
  local encoded
  encoded="$(printf 'set -e\n%s\n' "$*" | base64 | tr -d '\r\n')" || return
  shell "printf %s $encoded | base64 -d | su -c sh"
}
package_present() {
  local paths
  paths="$(shell pm path "$1" 2>/dev/null)" || return 1
  printf '%s\n' "$paths" | tr -d '\r' | grep -q '^package:'
}
state="$("$ADB" "${ADB_ARGS[@]}" get-state 2>/dev/null | tr -d '\r')" || exit 2
if [ "$state" != device ]; then echo "FAIL: The selected ADB device is not ready or authorized." >&2; exit 2; fi
echo "PASS: ADB device is reachable"
boot="$(shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')"
check "Android boot completed" test "$boot" = 1

root_id="$(root_shell id 2>/dev/null || true)"
check "Root is authorized" grep -Eq 'uid=0\(root\)' <<<"$root_id"
magisk_version="$(root_shell 'magisk -v' 2>/dev/null || true)"
check "Magisk daemon reports a version" test -n "$magisk_version"
printf 'INFO: Magisk version: %s\n' "${magisk_version:-unknown}"

zygisk="$(root_shell "magisk --sqlite \"SELECT value FROM settings WHERE key='zygisk';\"" 2>/dev/null | tr -d '\r' || true)"
modules="$(root_shell 'for d in /data/adb/modules/*; do [ -d "$d" ] || continue; id=${d##*/}; if [ -e "$d/remove" ]; then state=removing; elif [ -e "$d/disable" ]; then state=disabled; else state=enabled; fi; echo "$id:$state"; done' 2>/dev/null | tr -d '\r' || true)"
printf 'INFO: Modules:\n%s\n' "${modules:-  none detected}"
builtin=false
next=false
if grep -Eq '(^|=)1$' <<<"$zygisk"; then builtin=true; fi
if grep -Eq '^(zygisksu|zygisknext):enabled$' <<<"$modules"; then next=true; fi
if { "$builtin" && ! "$next"; } || { "$next" && ! "$builtin"; }; then
  echo "PASS: Exactly one Zygisk implementation is configured (runtime activation unverified)"
else
  echo "FAIL: Configure exactly one Zygisk implementation; zero or conflicting implementations found."
  failures=$((failures + 1))
fi

abi="$(shell getprop ro.product.cpu.abilist 2>/dev/null | tr -d '\r')"
bridge="$(shell getprop ro.dalvik.vm.native.bridge 2>/dev/null | tr -d '\r')"
fingerprint="$(shell getprop ro.build.fingerprint 2>/dev/null | tr -d '\r')"
printf 'INFO: ABI list: %s\nINFO: Native bridge property: %s\nINFO: Fingerprint: %s\n' "${abi:-unknown}" "${bridge:-unset}" "${fingerprint:-unknown}"
check "Google Play services package is installed" package_present com.google.android.gms
check "Google Play Store package is installed" package_present com.android.vending

echo "UNVERIFIED: Execute a known ARM/ARM64 test app and check native-library loading. ABI and bridge properties do not prove ARM translation works."
echo "UNVERIFIED: Check Play Store certification in the app and obtain a current app/backend Play Integrity verdict."
echo "UNVERIFIED: Install and launch the target app, check login and required behavior, and verify app-visible identity uniqueness after cloning."
echo "UNVERIFIED: Validate graphics, persistence after reboot, and resource usage at the intended fleet size."
if [ "$failures" -gt 0 ]; then echo "$failures automated diagnostic check(s) failed." >&2; exit 1; fi
echo "Automated diagnostics passed. Deployment acceptance remains pending the UNVERIFIED checks above."
