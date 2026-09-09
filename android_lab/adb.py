from __future__ import annotations

import os
import shlex
import subprocess

from .config import positive_number


class Adb:
    def __init__(self, executable: str = "adb", serial: str = "emulator-5554",
                 server: str = "tcp:127.0.0.1:5037", timeout_s: float = 30):
        positive_number(timeout_s, 'ADB timeout')
        self.executable, self.serial = executable, serial
        self.env = {**os.environ, "ADB_SERVER_SOCKET": server}
        self.timeout = timeout_s

    def command(self, *args: str) -> list[str]:
        return [self.executable, "-s", self.serial, *args]

    def run(self, *args: str, timeout: float | None = None, binary: bool = False) -> str | bytes:
        effective_timeout = self.timeout if timeout is None else timeout
        positive_number(effective_timeout, 'ADB timeout')
        try:
            result = subprocess.run(self.command(*args), env=self.env,
                                    capture_output=True, text=not binary,
                                    encoding=None if binary else 'utf-8',
                                    errors=None if binary else 'replace',
                                    timeout=effective_timeout, check=True)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"ADB executable was not found: {self.executable}. Install Android platform-tools or configure adb.executable.") from exc
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"ADB command timed out after {effective_timeout}s for {self.serial}; check the selected device and its authorization.") from exc
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr or exc.stdout or 'no device error output'
            if isinstance(detail, bytes):
                detail = detail.decode('utf-8', errors='replace')
            raise RuntimeError(f"ADB failed for {self.serial}: {str(detail).strip()}") from exc
        return result.stdout

    def connect(self) -> str:
        """Connect a configured TCP endpoint and verify it is authorized."""
        import ipaddress
        host, separator, port = self.serial.rpartition(':')
        if not separator or not port.isdigit() or not 1 <= int(port) <= 65535:
            raise ValueError('Use a TCP ADB serial HOST:PORT for connect')
        if host.startswith('[') and host.endswith(']'):
            ipaddress.IPv6Address(host[1:-1])
        elif not host or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-' for c in host):
            raise ValueError('Invalid ADB hostname')
        result = str(self.run('connect', self.serial)).strip()
        if any(word in result.lower() for word in ('failed', 'unable', 'cannot')):
            raise RuntimeError(f'ADB connection failed: {result}')
        if str(self.run('get-state')).strip() != 'device':
            raise RuntimeError('ADB endpoint is not authorized; approve debugging in the Android guest')
        return result

    def shell(self, *args: str, timeout: float | None = None) -> str:
        # adb joins shell arguments; explicitly quote each one for the device shell.
        return str(self.run("shell", shlex.join(args), timeout=timeout)).strip()

    def screenshot(self) -> bytes:
        data = self.run("exec-out", "screencap", "-p", binary=True)
        if not isinstance(data, bytes) or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("Device did not return a PNG screenshot")
        return data
