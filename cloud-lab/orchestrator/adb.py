from __future__ import annotations

import os
import shlex
import subprocess


class Adb:
    def __init__(self, executable: str = "adb", serial: str = "emulator-5554",
                 server: str = "tcp:127.0.0.1:5037", timeout_s: float = 30):
        self.executable, self.serial = executable, serial
        self.env = {**os.environ, "ADB_SERVER_SOCKET": server}
        self.timeout = timeout_s

    def command(self, *args: str) -> list[str]:
        return [self.executable, "-s", self.serial, *args]

    def run(self, *args: str, timeout: float | None = None, binary: bool = False) -> str | bytes:
        result = subprocess.run(self.command(*args), env=self.env,
                                capture_output=True, text=not binary,
                                encoding=None if binary else 'utf-8',
                                errors=None if binary else 'replace',
                                timeout=timeout or self.timeout, check=True)
        return result.stdout

    def shell(self, *args: str, timeout: float | None = None) -> str:
        # adb joins shell arguments; explicitly quote each one for the device shell.
        return str(self.run("shell", shlex.join(args), timeout=timeout)).strip()

    def screenshot(self) -> bytes:
        data = self.run("exec-out", "screencap", "-p", binary=True)
        if not isinstance(data, bytes) or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("Device did not return a PNG screenshot")
        return data
