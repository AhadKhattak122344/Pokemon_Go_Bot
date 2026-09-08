from __future__ import annotations

import subprocess
import time

from .adb import Adb


def wait_ready(adb: Adb, timeout_s: float = 600) -> None:
    deadline, delay = time.monotonic() + timeout_s, 1.0
    last_error = "device not booted"
    while time.monotonic() < deadline:
        try:
            remaining = max(0.1, min(10.0, deadline - time.monotonic()))
            if str(adb.run("get-state", timeout=remaining)).strip() == "device":
                remaining = max(0.1, min(10.0, deadline - time.monotonic()))
                if adb.shell("getprop", "sys.boot_completed", timeout=remaining) == "1":
                    return
        except (subprocess.SubprocessError, OSError) as exc:
            last_error = str(exc)
        time.sleep(max(0, min(delay, deadline - time.monotonic())))
        delay = min(delay * 2, 10)
    raise TimeoutError(f"Android did not finish booting within {timeout_s}s: {last_error}")
