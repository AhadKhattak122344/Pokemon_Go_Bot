"""Read-only Android evidence capture, independent of app launch or root."""
from __future__ import annotations

import json
from pathlib import Path
import time

from .adb import Adb
from .config import package_name


def capture(adb: Adb, out: Path, package: str | None = None) -> dict:
    """Save logs and device state without clearing logs or modifying the guest.

    Partial evidence is retained and failures are explicit in report.json. A
    successful capture proves collection only, not certification or sign-in.
    """
    if package:
        package_name(package)
    out.mkdir(parents=True, exist_ok=False)
    report = {"serial": adb.serial, "started": time.time(), "errors": {},
              "status": "collecting", "certification": "manual_check_required",
              "authentication": "unverified"}
    probes = {
        "device-state.txt": ("get-state",),
        "android-release.txt": ("shell", "getprop ro.build.version.release"),
        "android-sdk.txt": ("shell", "getprop ro.build.version.sdk"),
        "abi.txt": ("shell", "getprop ro.product.cpu.abilist"),
        "native-bridge.txt": ("shell", "getprop ro.dalvik.vm.native.bridge"),
        "boot.txt": ("shell", "getprop sys.boot_completed"),
        "device-time.txt": ("shell", "date -u"),
        "play-services.txt": ("shell", "dumpsys package com.google.android.gms"),
        "play-store.txt": ("shell", "dumpsys package com.android.vending"),
        "logcat.txt": ("logcat", "-b", "all", "-d"),
        "crash.txt": ("logcat", "-b", "crash", "-d"),
    }
    if package:
        probes["target-package.txt"] = ("shell", f"dumpsys package {package}")
    for filename, command in probes.items():
        try:
            value = str(adb.run(*command))
            (out / filename).write_text(value, encoding="utf-8")
            if filename == "device-state.txt" and value.strip() != "device":
                raise RuntimeError("ADB device is offline or unauthorized")
        except (OSError, RuntimeError) as exc:
            report["errors"][filename] = str(exc)
    try:
        (out / "screen.png").write_bytes(adb.screenshot())
    except (OSError, RuntimeError) as exc:
        report["errors"]["screen.png"] = str(exc)
    report.update(ended=time.time(), status="partial" if report["errors"] else "captured")
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if report["errors"]:
        raise RuntimeError(f"Diagnostic capture incomplete; inspect {out / 'report.json'}")
    return report
