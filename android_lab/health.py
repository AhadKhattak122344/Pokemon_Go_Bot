from __future__ import annotations

import subprocess
import time

from .adb import Adb
from .config import positive_number


def wait_ready(adb: Adb, timeout_s: float = 600) -> None:
    positive_number(timeout_s, 'Boot timeout')
    deadline, delay = time.monotonic() + timeout_s, 1.0
    last_error = "device not booted"
    while time.monotonic() < deadline:
        try:
            remaining = max(0.1, min(10.0, deadline - time.monotonic()))
            state = str(adb.run("get-state", timeout=remaining)).strip()
            last_error = f'ADB state: {state or "unavailable"}'
            if state == "device":
                remaining = max(0.1, min(10.0, deadline - time.monotonic()))
                boot = adb.shell("getprop", "sys.boot_completed", timeout=remaining)
                last_error = f'sys.boot_completed={boot or "unset"}'
                if boot == "1":
                    remaining = max(0.1, min(10.0, deadline - time.monotonic()))
                    if adb.shell('pm', 'path', 'android', timeout=remaining).startswith('package:'):
                        return
                    last_error = 'Android package manager is not ready'
        except FileNotFoundError:
            raise
        except (subprocess.SubprocessError, OSError, RuntimeError) as exc:
            last_error = str(exc)
        time.sleep(max(0, min(delay, deadline - time.monotonic())))
        delay = min(delay * 2, 10)
    raise TimeoutError(f"Android did not finish booting within {timeout_s}s: {last_error}")
